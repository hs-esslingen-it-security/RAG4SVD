#!/usr/bin/env python3
"""Convert PrimeVul train paired data into Vul-RAG knowledge-extraction input.
"""

from __future__ import annotations

import argparse
import difflib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# This script lives in vul-rag's own train-data folder. By default it reads
# primevul_train_paired.jsonl from -- and writes its combined output and the
# per-CWE *_data.json splits into -- this same folder; drop your
# PrimeVul-paired checkout's file here, or point elsewhere with --input/
# --output/--cwe-split-dir.
DATA_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = DATA_DIR / "primevul_train_paired.jsonl"
DEFAULT_OUTPUT = DATA_DIR / "primevul_train_paired_vulrag.json"
DEFAULT_CWE_SPLIT_DIR = DATA_DIR


@dataclass
class AdapterStats:
    total_input_rows: int = 0
    converted_records: int = 0
    invalid_pairs: int = 0
    fallback_cve_ids: int = 0


class PrimeVulTrainPairedToVulRagAdapter:
    def __init__(
        self,
        input_path: Path,
        output_path: Path,
        cwe_split_dir: Path | None = DEFAULT_CWE_SPLIT_DIR,
        strict_pairs: bool = False,
    ) -> None:
        self.input_path = input_path
        self.output_path = output_path
        self.cwe_split_dir = cwe_split_dir
        self.strict_pairs = strict_pairs
        self.stats = AdapterStats()
        self.invalid_pair_examples: list[dict[str, Any]] = []

    def run(self) -> list[dict[str, Any]]:
        rows = self._load_jsonl(self.input_path)
        converted = self._convert_rows(rows)
        self._write_json(self.output_path, converted)

        split_files: list[str] = []
        records_per_cwe: dict[str, int] = {}
        if self.cwe_split_dir is not None:
            split_files, records_per_cwe = self._write_cwe_splits(converted, self.cwe_split_dir)

        self._write_report(converted, split_files, records_per_cwe)
        return converted

    def _load_jsonl(self, path: Path) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                row["_line_number"] = line_number
                rows.append(row)
        self.stats.total_input_rows = len(rows)
        return rows

    def _convert_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        if not rows:
            return converted

        if len(rows) % 2 != 0:
            raise ValueError(
                f"Expected an even number of rows for paired PrimeVul input, got {len(rows)}."
            )

        for pair_start in range(0, len(rows), 2):
            first = rows[pair_start]
            second = rows[pair_start + 1]
            try:
                vulnerable_row, patched_row = self._validate_and_order_pair(first, second)
            except ValueError as exc:
                self._record_invalid_pair(first, second, str(exc))
                if self.strict_pairs:
                    raise
                continue
            converted.append(self._build_output_record(len(converted), vulnerable_row, patched_row))

        self.stats.converted_records = len(converted)
        return converted

    def _validate_and_order_pair(
        self, first: dict[str, Any], second: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        first_target = first.get("target")
        second_target = second.get("target")

        if first_target == 1 and second_target == 0:
            vulnerable_row, patched_row = first, second
        elif first_target == 0 and second_target == 1:
            vulnerable_row, patched_row = second, first
        else:
            raise ValueError(
                "Invalid PrimeVul paired rows at lines "
                f"{first['_line_number']} and {second['_line_number']}: "
                f"expected one target=1 row and one target=0 row, got "
                f"{first_target!r} and {second_target!r}."
            )

        self._assert_matching_pair_fields(vulnerable_row, patched_row)
        return vulnerable_row, patched_row

    def _assert_matching_pair_fields(
        self, vulnerable_row: dict[str, Any], patched_row: dict[str, Any]
    ) -> None:
        comparable_fields = (
            "commit_id",
            "project",
            "cve",
            "cwe",
            "cve_desc",
            "cve_description",
        )

        mismatches: list[str] = []
        for field in comparable_fields:
            left = self._normalize_comparable_value(vulnerable_row.get(field))
            right = self._normalize_comparable_value(patched_row.get(field))
            if left != right:
                mismatches.append(
                    f"{field}: {vulnerable_row.get(field)!r} != {patched_row.get(field)!r}"
                )

        if mismatches:
            raise ValueError(
                "PrimeVul pair validation failed for adjacent rows "
                f"{vulnerable_row['_line_number']} and {patched_row['_line_number']}. "
                "Mismatched fields: " + "; ".join(mismatches)
            )

    def _record_invalid_pair(
        self, first: dict[str, Any], second: dict[str, Any], reason: str
    ) -> None:
        self.stats.invalid_pairs += 1
        if len(self.invalid_pair_examples) >= 10:
            return
        self.invalid_pair_examples.append(
            {
                "first_line": first.get("_line_number"),
                "second_line": second.get("_line_number"),
                "first_idx": first.get("idx"),
                "second_idx": second.get("idx"),
                "first_target": first.get("target"),
                "second_target": second.get("target"),
                "first_commit_id": first.get("commit_id"),
                "second_commit_id": second.get("commit_id"),
                "first_cve": first.get("cve"),
                "second_cve": second.get("cve"),
                "reason": reason,
            }
        )

    def _build_output_record(
        self,
        output_id: int,
        vulnerable_row: dict[str, Any],
        patched_row: dict[str, Any],
    ) -> dict[str, Any]:
        cve_id = self._resolve_cve_id(vulnerable_row, patched_row, output_id)
        cwe_values = self._resolve_cwe(vulnerable_row, patched_row)
        code_before = self._first_non_empty(vulnerable_row.get("func"), "")
        code_after = self._first_non_empty(patched_row.get("func"), "")
        patch, modified_lines = self._build_diff(code_before, code_after)

        record = {
            "id": output_id,
            "cve_id": cve_id,
            "code_before_change": code_before,
            "code_after_change": code_after,
            "cwe": cwe_values,
            "cve_description": self._first_non_empty(
                vulnerable_row.get("cve_description"),
                vulnerable_row.get("cve_desc"),
                patched_row.get("cve_description"),
                patched_row.get("cve_desc"),
                "",
            ),
            "patch": patch,
            "function_modified_lines": modified_lines,
        }

        return record

    @staticmethod
    def _build_diff(code_before: str, code_after: str) -> tuple[str, dict[str, list[str]]]:
        before_lines = code_before.splitlines(keepends=True)
        after_lines = code_after.splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(before_lines, after_lines, fromfile="code before", tofile="code after")
        )

        added: list[str] = []
        deleted: list[str] = []
        for line in diff_lines:
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                continue
            if line.startswith("+"):
                added.append(line[1:].rstrip("\n"))
            elif line.startswith("-"):
                deleted.append(line[1:].rstrip("\n"))

        patch = "".join(diff_lines).rstrip("\n")
        return patch, {"added": added, "deleted": deleted}

    def _resolve_cwe(
        self, vulnerable_row: dict[str, Any], patched_row: dict[str, Any]
    ) -> list[str]:
        raw_value = self._first_non_empty(
            vulnerable_row.get("cwe_label"),
            vulnerable_row.get("cwe"),
            patched_row.get("cwe_label"),
            patched_row.get("cwe"),
            None,
        )

        if isinstance(raw_value, list):
            cleaned = [str(item) for item in raw_value if item not in (None, "", "None")]
            return cleaned or ["CWE-UNKNOWN"]
        if raw_value in (None, "", "None"):
            return ["CWE-UNKNOWN"]
        return [str(raw_value)]

    def _resolve_cve_id(
        self,
        vulnerable_row: dict[str, Any],
        patched_row: dict[str, Any],
        output_id: int,
    ) -> str:
        commit_metadata = self._first_non_empty(
            vulnerable_row.get("commit_metadata"), patched_row.get("commit_metadata"), None
        )
        if commit_metadata not in (None, "", "None"):
            return str(commit_metadata)

        fallback = self._first_non_empty(
            vulnerable_row.get("cve"),
            vulnerable_row.get("commit_id"),
            patched_row.get("cve"),
            patched_row.get("commit_id"),
            None,
        )
        if fallback not in (None, "", "None"):
            self.stats.fallback_cve_ids += 1
            return str(fallback)

        self.stats.fallback_cve_ids += 1
        return f"UNKNOWN-{output_id}"

    def _write_cwe_splits(
        self, converted: list[dict[str, Any]], splits_dir: Path
    ) -> tuple[list[str], dict[str, int]]:
        splits_dir.mkdir(parents=True, exist_ok=True)
        buckets: dict[str, list[dict[str, Any]]] = {}
        for record in converted:
            buckets.setdefault(record["cwe"][0], []).append(record)

        written: list[str] = []
        counts: dict[str, int] = {}
        for cwe_id, records in sorted(buckets.items()):
            path = splits_dir / f"primevul_{cwe_id}_data.json"
            self._write_json(path, records)
            written.append(str(path))
            counts[cwe_id] = len(records)

        return written, counts

    def _write_json(self, path: Path, data: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)

    def _write_report(
        self,
        converted: list[dict[str, Any]],
        split_files: list[str],
        records_per_cwe: dict[str, int],
    ) -> None:
        report = {
            "input_file": str(self.input_path),
            "output_file": str(self.output_path),
            "total_input_rows": self.stats.total_input_rows,
            "converted_records": self.stats.converted_records,
            "invalid_pairs": self.stats.invalid_pairs,
            "fallback_cve_ids": self.stats.fallback_cve_ids,
            "strict_pairs": self.strict_pairs,
            "invalid_pair_examples": self.invalid_pair_examples,
            "cwe_split_dir": str(self.cwe_split_dir) if self.cwe_split_dir is not None else None,
            "cwe_split_files": split_files,
            "records_per_cwe": records_per_cwe,
        }
        report_path = self.output_path.with_name(self.output_path.stem + "_report.json")
        with report_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)

    @staticmethod
    def _first_non_empty(*values: Any) -> Any:
        for value in values:
            if value not in (None, "", "None"):
                return value
        return None

    @staticmethod
    def _normalize_comparable_value(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(str(item) for item in value)
        return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PrimeVul train paired JSONL into Vul-RAG training data, split per CWE."
    )
    parser.add_argument(
        "--input",
        "-i",
        default=str(DEFAULT_INPUT),
        help=f"Input PrimeVul train paired JSONL file (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=str(DEFAULT_OUTPUT),
        help=f"Combined output Vul-RAG JSON file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--cwe-split-dir",
        default=str(DEFAULT_CWE_SPLIT_DIR),
        help=(
            "Directory to write one primevul_<CWE-id>_data.json file per CWE into, as consumed by "
            f"generate_knowledge.sh (default: {DEFAULT_CWE_SPLIT_DIR})"
        ),
    )
    parser.add_argument(
        "--no-cwe-splits",
        action="store_true",
        help="Skip writing per-CWE split files; only write the combined output file.",
    )
    parser.add_argument(
        "--strict-pairs",
        action="store_true",
        help="Abort on the first invalid adjacent pair instead of skipping invalid pairs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    adapter = PrimeVulTrainPairedToVulRagAdapter(
        input_path=Path(args.input).resolve(),
        output_path=Path(args.output).resolve(),
        cwe_split_dir=None if args.no_cwe_splits else Path(args.cwe_split_dir).resolve(),
        strict_pairs=args.strict_pairs,
    )

    if not adapter.input_path.exists():
        raise FileNotFoundError(f"Input file not found: {adapter.input_path}")

    adapter.run()

    print(f"Input rows: {adapter.stats.total_input_rows}")
    print(f"Converted records: {adapter.stats.converted_records}")
    print(f"Invalid adjacent pairs skipped: {adapter.stats.invalid_pairs}")
    print(f"Fallback cve_id count: {adapter.stats.fallback_cve_ids}")
    print(f"Combined output written to: {adapter.output_path}")
    if adapter.cwe_split_dir is not None:
        print(f"Per-CWE split files written to: {adapter.cwe_split_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
