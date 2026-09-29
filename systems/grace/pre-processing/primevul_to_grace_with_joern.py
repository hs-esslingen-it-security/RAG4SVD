#!/usr/bin/env python3
"""Convert PrimeVul paired JSONL splits into GRACE-ready JSON datasets with
Joern graph fields and a leak-free, retrieval-based in-context-learning example.

Replaces the previous _build_example_map, which assigned each row's own
pair-partner (the same function's vulnerable/patched counterpart) as its
"example" field -- a 100% answer leak. Examples are now drawn from an
independent train+valid candidate pool via ExampleRetriever (see
grace_example_retriever.py), excluding each row's own pool entry and its own
pair-partner.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from grace_example_retriever import CodeEmbedder, Candidate, ExampleRetriever, jaccard, node_type_sequence


# This script lives in GRACE's own data folder. By default it reads
# primevul_{split}_paired.jsonl from -- and writes primevul_{split}_paired_grace_joern_id.json
# into -- this same folder; drop your PrimeVul-paired checkout's files here,
# or point elsewhere with --input-dir/--output-dir. DEFAULT_JOERN_ROOT expects
# a joern-parse checkout in a "joern" subfolder next to this script (see
# --joern-root to point at a different install).
DATA_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = DATA_DIR
DEFAULT_OUTPUT_DIR = DATA_DIR
DEFAULT_JOERN_ROOT = DATA_DIR / "joern"
DEFAULT_SPLITS = ("train", "valid", "test")
DEFAULT_LIVE_TEST_PATH = DATA_DIR / "primevul_test_paired_grace_joern_id.json"
CANDIDATE_POOL_SPLITS = ("train", "valid")


@dataclass
class AdapterStats:
    split: str = ""
    total_input_rows: int = 0
    converted_records: int = 0
    orphan_rows: int = 0
    joern_batch_failures: int = 0
    joern_single_fallbacks: int = 0
    joern_extraction_errors: int = 0
    reused_existing_graph: int = 0
    examples_assigned: int = 0
    examples_missing: int = 0
    identity_leak_count: int = 0
    text_prefix_collisions: int = 0
    max_pair_partner_jaccard: float = 0.0
    pair_partner_jaccard_gt_0_9: int = 0


class PrimeVulToGraceWithJoernAdapter:
    def __init__(
        self,
        input_dir: Path,
        output_dir: Path,
        joern_root: Path,
        use_joern: bool = True,
        embedder: CodeEmbedder | None = None,
        joern_batch_size: int = 100,
        reuse_test_graph_path: Path | None = DEFAULT_LIVE_TEST_PATH,
    ) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.joern_root = joern_root
        self.use_joern = use_joern
        self._embedder = embedder
        self.joern_batch_size = joern_batch_size
        self.reuse_test_graph_path = reuse_test_graph_path

    @property
    def embedder(self) -> CodeEmbedder:
        if self._embedder is None:
            self._embedder = CodeEmbedder()
        return self._embedder

    # ---- top-level orchestration ----

    def run(self, splits: tuple[str, ...] = DEFAULT_SPLITS) -> dict[str, list[dict[str, Any]]]:
        raw_rows: dict[str, list[dict[str, Any]]] = {}
        stats_by_split: dict[str, AdapterStats] = {}

        for split in splits:
            rows = self._load_jsonl(self._resolve_input_path(split))
            stats = AdapterStats(split=split, total_input_rows=len(rows))
            stats.orphan_rows = self._assign_pair_ids(rows, split)
            raw_rows[split] = rows
            stats_by_split[split] = stats

        graphs: dict[str, dict[int, tuple[str, str]]] = {}
        for split in splits:
            stats = stats_by_split[split]
            if (
                split == "test"
                and self.reuse_test_graph_path is not None
                and self.reuse_test_graph_path.exists()
            ):
                graphs[split] = self._reuse_existing_graphs(raw_rows[split], split, stats)
            elif self.use_joern:
                graphs[split] = self._extract_joern_graphs_batch(raw_rows[split], split, stats)
            else:
                graphs[split] = {
                    row["_line_number"]: self._build_graph_text(str(row["func"]))
                    for row in raw_rows[split]
                }

        pool_splits = tuple(s for s in CANDIDATE_POOL_SPLITS if s in splits)
        candidates = self._build_candidate_pool(raw_rows, graphs, pool_splits)
        retriever = ExampleRetriever(self.embedder, top_k=5)
        retriever.build_corpus(candidates)
        func_text_index = self._build_func_text_index(candidates)

        outputs: dict[str, list[dict[str, Any]]] = {}
        for split in splits:
            stats = stats_by_split[split]
            converted = self._assign_examples_and_build_output(
                raw_rows[split], graphs[split], split, retriever, func_text_index, stats
            )
            stats.converted_records = len(converted)
            self._run_leak_checks(converted, stats)

            output_path = self._resolve_output_path(split)
            self._write_json(output_path, converted)
            self._write_report(output_path, stats)
            outputs[split] = converted

        return outputs

    # ---- input / pairing ----

    def _resolve_input_path(self, split: str) -> Path:
        path = self.input_dir / f"primevul_{split}_paired.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        return path

    def _resolve_output_path(self, split: str) -> Path:
        return self.output_dir / f"primevul_{split}_paired_grace_joern_id.json"

    def _load_jsonl(self, path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                row["_line_number"] = line_number
                func = row.get("func")
                if func in (None, ""):
                    raise ValueError(f"Missing func in input row at line {line_number} of {path}")
                target = row.get("target")
                if target not in (0, 1, "0", "1"):
                    raise ValueError(f"Invalid target in input row at line {line_number} of {path}: {target!r}")
                rows.append(row)
        return rows

    def _assign_pair_ids(self, rows: list[dict[str, Any]], split: str) -> int:
        """Assigns row['pair_id'] in place; returns the orphan-row count.

        Rows belonging to the same commit are grouped and matched by opposite
        target, in file order. Most commits contribute exactly one vulnerable +
        one patched row (a clean pair); at full dataset scale some commits also
        carry extra same-target context rows (e.g. other non-vulnerable functions
        touched by the same commit) with no counterpart -- separating by target
        first and zipping the matched counts (rather than assuming strict
        alternation every 2 rows) correctly pairs the real vulnerable/patched
        rows and leaves any surplus as orphans instead of raising on a same-target
        collision.
        """
        commit_groups: dict[Any, list[dict[str, Any]]] = {}
        for row in rows:
            commit_groups.setdefault(row.get("commit_id"), []).append(row)

        orphan_rows = 0
        for commit_id, group in commit_groups.items():
            vulnerable = [row for row in group if str(row.get("target")) == "1"]
            patched = [row for row in group if str(row.get("target")) == "0"]

            for row_a, row_b in zip(vulnerable, patched):
                shared_id = f"{commit_id}_{row_a.get('idx')}_{row_b.get('idx')}"
                row_a["pair_id"] = shared_id
                row_b["pair_id"] = shared_id

            surplus = vulnerable[len(patched) :] + patched[len(vulnerable) :]
            for orphan in surplus:
                orphan["pair_id"] = f"{commit_id}_orphan_{orphan.get('idx')}"
                orphan_rows += 1

        return orphan_rows

    def _pair_partner_pool_ids(self, rows: list[dict[str, Any]], split: str) -> dict[int, str]:
        by_pair_id: dict[str, list[int]] = {}
        for row in rows:
            by_pair_id.setdefault(row["pair_id"], []).append(row["_line_number"])

        partner_pool_id: dict[int, str] = {}
        for line_nos in by_pair_id.values():
            if len(line_nos) == 2:
                a, b = line_nos
                partner_pool_id[a] = f"{split}:{b}"
                partner_pool_id[b] = f"{split}:{a}"
        return partner_pool_id

    # ---- graph reuse (test split) ----

    def _reuse_existing_graphs(
        self, rows: list[dict[str, Any]], split: str, stats: AdapterStats
    ) -> dict[int, tuple[str, str]]:
        existing = json.loads(self.reuse_test_graph_path.read_text(encoding="utf-8"))
        if len(existing) != len(rows) or any(
            row["func"] != existing_row.get("func") for row, existing_row in zip(rows, existing)
        ):
            # Order/content assumption doesn't hold -- fall back to recomputing.
            if self.use_joern:
                return self._extract_joern_graphs_batch(rows, split, stats)
            return {row["_line_number"]: self._build_graph_text(str(row["func"])) for row in rows}

        graphs: dict[int, tuple[str, str]] = {}
        for row, existing_row in zip(rows, existing):
            graphs[row["_line_number"]] = (str(existing_row.get("node", "")), str(existing_row.get("edge", "")))
            stats.reused_existing_graph += 1
        return graphs

    # ---- Joern extraction: batched (train/valid) ----

    def _extract_joern_graphs_batch(
        self, rows: list[dict[str, Any]], split: str, stats: AdapterStats
    ) -> dict[int, tuple[str, str]]:
        if not self.joern_root.exists():
            raise FileNotFoundError(f"Joern root not found: {self.joern_root}")

        graphs: dict[int, tuple[str, str]] = {}
        for start in range(0, len(rows), self.joern_batch_size):
            batch = rows[start : start + self.joern_batch_size]
            graphs.update(self._run_batch_with_bisection(batch, split, stats))
        return graphs

    def _run_batch_with_bisection(
        self, batch: list[dict[str, Any]], split: str, stats: AdapterStats
    ) -> dict[int, tuple[str, str]]:
        try:
            return self._run_joern_batch(batch, split)
        except RuntimeError:
            stats.joern_batch_failures += 1
            if len(batch) == 1:
                row = batch[0]
                try:
                    stats.joern_single_fallbacks += 1
                    return {row["_line_number"]: self._extract_joern_graph_single(str(row["func"]), row["_line_number"])}
                except Exception:
                    stats.joern_extraction_errors += 1
                    return {row["_line_number"]: ("", "")}
            mid = len(batch) // 2
            result: dict[int, tuple[str, str]] = {}
            result.update(self._run_batch_with_bisection(batch[:mid], split, stats))
            result.update(self._run_batch_with_bisection(batch[mid:], split, stats))
            return result

    def _run_joern_batch(self, batch: list[dict[str, Any]], split: str) -> dict[int, tuple[str, str]]:
        with tempfile.TemporaryDirectory(prefix=f"primevul_joern_{split}_") as tmpdir:
            tmp_root = Path(tmpdir)
            source_dir = tmp_root / "source"
            source_dir.mkdir(parents=True, exist_ok=True)

            filenames: dict[int, str] = {}
            for row in batch:
                line_no = row["_line_number"]
                filename = f"{split}_{line_no:06d}.c"
                (source_dir / filename).write_text(str(row["func"]), encoding="utf-8")
                filenames[line_no] = filename

            output_dir = tmp_root / "out"
            command = ["bash", "./joern-parse", str(source_dir), str(output_dir)]
            try:
                subprocess.run(
                    command,
                    cwd=self.joern_root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=900,
                )
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    f"Joern batch parse failed for split={split}: {exc.stderr.strip() or exc.stdout.strip() or exc}"
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError(f"Joern batch parse timed out for split={split}: {exc}") from exc

            results: dict[int, tuple[str, str]] = {}
            for line_no, filename in filenames.items():
                node_matches = list(output_dir.rglob(f"{filename}/nodes.csv"))
                edge_matches = list(output_dir.rglob(f"{filename}/edges.csv"))
                if len(node_matches) != 1 or len(edge_matches) != 1:
                    raise RuntimeError(
                        f"Ambiguous or missing Joern output for {filename}: "
                        f"nodes={len(node_matches)} edges={len(edge_matches)}"
                    )
                node_text = self._serialize_csv(node_matches[0], limit=2000)
                edge_text = self._serialize_csv(edge_matches[0], limit=2000)
                results[line_no] = (node_text, edge_text)
            return results

    # ---- Joern extraction: single-file fallback ----

    def _extract_joern_graph_single(self, func: str, line_number: int | None) -> tuple[str, str]:
        with tempfile.TemporaryDirectory(prefix="primevul_joern_single_") as tmpdir:
            tmp_root = Path(tmpdir)
            source_dir = tmp_root / "source"
            source_dir.mkdir(parents=True, exist_ok=True)
            source_file = source_dir / "sample.c"
            source_file.write_text(func, encoding="utf-8")

            output_dir = tmp_root / "out"
            command = ["bash", "./joern-parse", str(source_dir), str(output_dir)]
            try:
                subprocess.run(
                    command,
                    cwd=self.joern_root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=120,
                )
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    f"Joern parsing failed for input row {line_number}: {exc.stderr.strip() or exc.stdout.strip() or exc}"
                ) from exc

            node_file = self._select_best_csv(output_dir, "nodes.csv")
            edge_file = self._select_best_csv(output_dir, "edges.csv")
            if node_file is None or edge_file is None:
                raise RuntimeError(
                    f"Joern output incomplete for input row {line_number}: "
                    f"nodes.csv={node_file is not None}, edges.csv={edge_file is not None}"
                )
            return self._serialize_csv(node_file, limit=2000), self._serialize_csv(edge_file, limit=2000)

    def _select_best_csv(self, root: Path, name: str) -> Path | None:
        if not root.exists():
            return None
        candidates = [path for path in root.rglob(name) if path.is_file()]
        if not candidates:
            return None

        def score(path: Path) -> tuple[int, int]:
            try:
                with path.open("r", encoding="utf-8", newline="") as handle:
                    row_count = sum(1 for _ in handle) - 1
            except OSError:
                row_count = -1
            return row_count, len(path.parts)

        return max(candidates, key=score)

    # ---- fast non-Joern fallback (--no-joern) ----

    def _build_graph_text(self, func: str) -> tuple[str, str]:
        lines = [line.rstrip() for line in func.splitlines()]
        node_lines: list[str] = []
        edge_lines: list[str] = []
        previous_node_id: str | None = None

        for line_number, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            node_id = f"N{len(node_lines) + 1}"
            node_kind = self._classify_line(stripped, node_lines == [])
            node_lines.append(
                f"{node_id} | line={line_number} | kind={node_kind} | text={self._compact_text(stripped, 180)}"
            )
            if previous_node_id is not None:
                edge_lines.append(f"{previous_node_id} -> {node_id} | type=next_line")
            previous_node_id = node_id
            if len(node_lines) >= 20:
                break

        return self._truncate_text("\n".join(node_lines), 2000), self._truncate_text("\n".join(edge_lines), 2000)

    def _classify_line(self, line: str, is_first_code_line: bool) -> str:
        lowered = line.lstrip()
        if is_first_code_line and "(" in lowered and ")" in lowered and lowered.endswith("{"):
            return "function_signature"
        if lowered.startswith("if ") or lowered.startswith("if(") or re.match(r"^else\s+if\b", lowered):
            return "branch"
        if lowered.startswith("else"):
            return "branch"
        if lowered.startswith("for ") or lowered.startswith("for("):
            return "loop"
        if lowered.startswith("while ") or lowered.startswith("while("):
            return "loop"
        if lowered.startswith("switch ") or lowered.startswith("switch("):
            return "branch"
        if lowered.startswith("case ") or lowered.startswith("default:"):
            return "branch"
        if lowered.startswith("return ") or lowered == "return;":
            return "return"
        if lowered.startswith("#include") or lowered.startswith("#define"):
            return "preprocessor"
        if "=" in lowered:
            return "assignment"
        if lowered.endswith(";"):
            return "statement"
        return "block"

    def _compact_text(self, text: str, limit: int) -> str:
        return self._truncate_text(" ".join(text.split()), limit)

    def _truncate_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 3)] + "..."

    def _serialize_csv(self, path: Path, limit: int) -> str:
        lines: list[str] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                if not row:
                    continue
                lines.append(self._format_csv_row(path.name, row))
                if len("\n".join(lines)) >= limit:
                    break
        text = "\n".join(lines)
        return text[:limit] if len(text) > limit else text

    def _format_csv_row(self, file_name: str, row: dict[str, str | None]) -> str:
        parts: list[str] = [f"source={file_name}"]
        for key, value in row.items():
            if value in (None, ""):
                continue
            cleaned_value = str(value).replace("\t", " ").replace("\n", " ")
            parts.append(f"{key}={cleaned_value}")
        return " | ".join(parts)

    # ---- example retrieval ----

    def _build_candidate_pool(
        self,
        raw_rows: dict[str, list[dict[str, Any]]],
        graphs: dict[str, dict[int, tuple[str, str]]],
        pool_splits: tuple[str, ...],
    ) -> list[Candidate]:
        candidates: list[Candidate] = []
        for split in pool_splits:
            for row in raw_rows[split]:
                line_no = row["_line_number"]
                node_text, _ = graphs[split][line_no]
                candidates.append(
                    Candidate(
                        pool_id=f"{split}:{line_no}",
                        pair_id=row["pair_id"],
                        func=str(row["func"]),
                        node_types=node_type_sequence(node_text),
                    )
                )
        return candidates

    def _build_func_text_index(self, candidates: list[Candidate]) -> dict[str, list[str]]:
        """Maps exact func text -> every candidate pool_id sharing that text.

        PrimeVul contains functions duplicated verbatim across unrelated
        commits/pair_ids (e.g. the same CVE fix backported to another branch).
        Exclusion by the query's own pair_id alone doesn't catch a *different*
        pair_id carrying identical text, so this index lets exclusion be
        extended pool-wide by content instead of only by declared identity.
        """
        index: dict[str, list[str]] = {}
        for candidate in candidates:
            index.setdefault(candidate.func, []).append(candidate.pool_id)
        return index

    def _assign_examples_and_build_output(
        self,
        rows: list[dict[str, Any]],
        graphs: dict[int, tuple[str, str]],
        split: str,
        retriever: ExampleRetriever,
        func_text_index: dict[str, list[str]],
        stats: AdapterStats,
    ) -> list[dict[str, Any]]:
        exclude_self = split in CANDIDATE_POOL_SPLITS
        partner_pool_id = self._pair_partner_pool_ids(rows, split) if exclude_self else {}
        partner_row_by_pair_id: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            partner_row_by_pair_id.setdefault(row["pair_id"], []).append(row)

        queries = []
        for row in rows:
            line_no = row["_line_number"]
            node_text, _ = graphs[line_no]
            query_types = node_type_sequence(node_text)
            query_func = str(row["func"])

            exclude_pool_ids: set[str] = set()
            if exclude_self:
                exclude_pool_ids.add(f"{split}:{line_no}")
                partner = partner_pool_id.get(line_no)
                if partner:
                    exclude_pool_ids.add(partner)

            # Exact-text exclusion, extended pool-wide via func_text_index: exclude
            # any candidate whose text matches the query's own func or its declared
            # pair-partner's func, regardless of which pair_id it nominally belongs to.
            exclude_funcs: set[str] = {query_func}
            same_pair_rows = partner_row_by_pair_id.get(row["pair_id"], [])
            for partner_row in same_pair_rows:
                if partner_row is not row:
                    exclude_funcs.add(str(partner_row["func"]))
            for text in list(exclude_funcs):
                exclude_pool_ids.update(func_text_index.get(text, []))

            queries.append((query_func, query_types, exclude_pool_ids, exclude_funcs))

        best_candidates = retriever.query_many(queries)

        converted: list[dict[str, Any]] = []
        for row, best, (_, _, exclude_pool_ids, _) in zip(rows, best_candidates, queries):
            line_no = row["_line_number"]
            node_text, edge_text = graphs[line_no]
            if best is not None:
                stats.examples_assigned += 1
                example_text = best.func[:4000]
                # Authoritative identity check: the chosen candidate must never be
                # the row's own pool entry or its declared pair-partner (by identity,
                # not by text -- see _run_leak_checks for why text alone is unreliable).
                if best.pool_id in exclude_pool_ids:
                    stats.identity_leak_count += 1
            else:
                stats.examples_missing += 1
                example_text = ""
            converted.append(
                {
                    "func": row["func"],
                    "target": int(row["target"]),
                    "node": node_text,
                    "edge": edge_text,
                    "example": example_text,
                    "pair_id": row["pair_id"],
                }
            )
        return converted

    # ---- verification ----

    def _run_leak_checks(self, converted: list[dict[str, Any]], stats: AdapterStats) -> None:
        """Informational text-based statistics, NOT the authoritative leak gate.

        stats.identity_leak_count (set in _assign_examples_and_build_output) is
        the authoritative check: it verifies by pool_id identity that the chosen
        candidate was never the excluded self/pair-partner entry, and must be 0.

        text_prefix_collisions below is a coincidental-prefix counter, not a leak
        count: PrimeVul contains some very large functions where two independent,
        correctly-non-excluded candidates share an identical leading N characters
        (example/func are both truncated to 4000 chars for the prompt) while
        differing later in the function -- this trips a literal prefix-equality
        check without the model ever having selected the partner. It's tracked so
        a genuine regression (rate back near the pre-fix ~100%) is still visible,
        but a low nonzero count here is expected and is not itself a failure.
        """
        by_pair: dict[str, list[dict[str, Any]]] = {}
        for record in converted:
            by_pair.setdefault(record["pair_id"], []).append(record)

        prefix_collisions = 0
        max_jaccard = 0.0
        gt_0_9 = 0
        for records in by_pair.values():
            if len(records) != 2:
                continue
            for record, partner in (records, reversed(records)):
                example = record.get("example", "")
                partner_func = partner.get("func", "")
                if example and example == partner_func[: len(example)]:
                    prefix_collisions += 1
                score = jaccard(example, partner_func) if example else 0.0
                max_jaccard = max(max_jaccard, score)
                if score > 0.9:
                    gt_0_9 += 1

        stats.text_prefix_collisions = prefix_collisions
        stats.max_pair_partner_jaccard = max_jaccard
        stats.pair_partner_jaccard_gt_0_9 = gt_0_9

    # ---- output ----

    def _write_json(self, path: Path, data: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def _write_report(self, output_path: Path, stats: AdapterStats) -> None:
        report_path = output_path.with_name(f"{output_path.stem}_report.json")
        report_path.write_text(json.dumps(dataclasses.asdict(stats), indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PrimeVul paired JSONL splits into GRACE-compatible JSON files with Joern graph fields."
    )
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help=f"Directory with primevul_*_paired.jsonl (default: {DEFAULT_INPUT_DIR})")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--joern-root", default=str(DEFAULT_JOERN_ROOT), help=f"Joern root directory containing joern-parse (default: {DEFAULT_JOERN_ROOT})")
    parser.add_argument("--splits", nargs="+", default=list(DEFAULT_SPLITS), choices=list(DEFAULT_SPLITS), help="Splits to convert (default: all)")
    parser.add_argument("--joern-batch-size", type=int, default=100, help="Functions per joern-parse invocation for train/valid (default: 100)")
    parser.add_argument("--no-joern", dest="use_joern", action="store_false", help="Disable Joern for graph extraction and use the fast built-in fallback instead.")
    parser.add_argument("--no-reuse-test-graph", dest="reuse_test_graph", action="store_false", help="Recompute test-split node/edge via Joern instead of reusing the live GRACE data file.")
    parser.add_argument("--live-test-path", default=str(DEFAULT_LIVE_TEST_PATH), help="Path to the existing live test JSON to reuse node/edge from.")
    parser.set_defaults(use_joern=True, reuse_test_graph=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    joern_root = Path(args.joern_root).resolve()
    reuse_test_graph_path = Path(args.live_test_path).resolve() if args.reuse_test_graph else None

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    adapter = PrimeVulToGraceWithJoernAdapter(
        input_dir=input_dir,
        output_dir=output_dir,
        joern_root=joern_root,
        use_joern=args.use_joern,
        joern_batch_size=args.joern_batch_size,
        reuse_test_graph_path=reuse_test_graph_path,
    )
    outputs = adapter.run(splits=tuple(args.splits))
    for split, rows in outputs.items():
        print(f"Converted {len(rows)} rows for split={split} into {output_dir}")


if __name__ == "__main__":
    main()
