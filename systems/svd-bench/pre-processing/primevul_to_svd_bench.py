#!/usr/bin/env python3
"""Convert paired PrimeVul JSONL splits into SVD-Bench compatible JSON datasets."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# This script lives in svd-bench's own PrimeVul data folder. By default it
# reads primevul_{split}_paired.jsonl from -- and writes primevul_{split}_svdbench.json
# into -- this same folder; drop your PrimeVul-paired checkout's files here,
# or point elsewhere with --input-dir/--output-dir.
DATA_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_DIR = DATA_DIR
DEFAULT_OUTPUT_DIR = DATA_DIR
DEFAULT_SPLITS = ("train", "valid", "test")


@dataclass
class AdapterStats:
    total_input_rows: int = 0
    converted_records: int = 0
    invalid_pairs: int = 0
    fallback_cwe_ids: int = 0


class PrimeVulToSVDBenchAdapter:
    def __init__(self, input_dir: Path, output_dir: Path, strict_pairs: bool = False) -> None:
        self.input_dir = input_dir
        self.output_dir = output_dir
        self.strict_pairs = strict_pairs

    def run(self, splits: tuple[str, ...] = DEFAULT_SPLITS) -> dict[str, list[dict[str, Any]]]:
        outputs: dict[str, list[dict[str, Any]]] = {}
        for split in splits:
            input_path = self._resolve_input_path(split)
            output_path = self._resolve_output_path(split)

            rows = self._load_jsonl(input_path)
            converted, stats, invalid_pair_examples = self._convert_rows(rows)

            self._write_json(output_path, converted)
            self._write_report(output_path, input_path, stats, invalid_pair_examples)
            outputs[split] = converted

        return outputs

    def _resolve_input_path(self, split: str) -> Path:
        path = self.input_dir / f"primevul_{split}_paired.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        return path

    def _resolve_output_path(self, split: str) -> Path:
        return self.output_dir / f"primevul_{split}_svdbench.json"

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
        return rows

    def _convert_rows(
        self, rows: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], AdapterStats, list[dict[str, Any]]]:
        stats = AdapterStats(total_input_rows=len(rows))
        invalid_pair_examples: list[dict[str, Any]] = []

        if not rows:
            return [], stats, invalid_pair_examples

        if len(rows) % 2 != 0:
            raise ValueError(f"Expected an even number of rows for paired PrimeVul input, got {len(rows)}.")

        converted: list[dict[str, Any]] = []
        for pair_start in range(0, len(rows), 2):
            first = rows[pair_start]
            second = rows[pair_start + 1]

            try:
                vulnerable_row, patched_row = self._validate_and_order_pair(first, second)
            except ValueError as exc:
                stats.invalid_pairs += 1
                if len(invalid_pair_examples) < 10:
                    invalid_pair_examples.append(
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
                            "reason": str(exc),
                        }
                    )
                if self.strict_pairs:
                    raise
                continue

            pair_id = self._generate_pair_id(vulnerable_row, patched_row)
            converted.append(self._build_output_record(vulnerable_row, pair_id))
            converted.append(self._build_output_record(patched_row, pair_id))

        stats.converted_records = len(converted)
        return converted, stats, invalid_pair_examples

    def _validate_and_order_pair(
        self, first: dict[str, Any], second: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        first_target = self._normalize_target(first.get("target"))
        second_target = self._normalize_target(second.get("target"))

        if first_target == 1 and second_target == 0:
            vulnerable_row, patched_row = first, second
        elif first_target == 0 and second_target == 1:
            vulnerable_row, patched_row = second, first
        else:
            raise ValueError(
                "Invalid PrimeVul paired rows at lines "
                f"{first['_line_number']} and {second['_line_number']}: "
                f"expected one target=1 row and one target=0 row, got {first.get('target')!r} and {second.get('target')!r}."
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
            "cwe_label",
            "cve_description",
            "cve_desc",
        )

        mismatches: list[str] = []
        for field in comparable_fields:
            left = self._normalize_comparable_value(vulnerable_row.get(field))
            right = self._normalize_comparable_value(patched_row.get(field))
            if left != right:
                mismatches.append(f"{field}: {vulnerable_row.get(field)!r} != {patched_row.get(field)!r}")

        if mismatches:
            raise ValueError(
                "PrimeVul pair validation failed for adjacent rows "
                f"{vulnerable_row['_line_number']} and {patched_row['_line_number']}. "
                "Mismatched fields: " + "; ".join(mismatches)
            )

    def _generate_pair_id(self, vulnerable_row: dict[str, Any], patched_row: dict[str, Any]) -> str:
        """Generate pair_id from commit_id + both rows' idx (unique per pair).

        commit_id + file_name alone can collide when a commit touches multiple
        functions in the same file (or file_name is missing), which silently
        merges unrelated pairs under svd-bench's pairwise-accuracy metric.
        idx is PrimeVul's per-row unique identifier, so combining it with both
        rows guarantees a unique pair_id (mirrors the scheme used by the GRACE
        adapter, primevul_to_grace_with_joern.py).
        """
        commit_id = vulnerable_row.get("commit_id", "unknown")
        return f"{commit_id}_{vulnerable_row.get('idx')}_{patched_row.get('idx')}"

    def _build_output_record(self, row: dict[str, Any], pair_id: str) -> dict[str, Any]:
        func = self._first_non_empty(row.get("func"), row.get("code_vulnerable"), row.get("code_patched"))
        if func in (None, ""):
            raise ValueError(f"Missing code content in input row at line {row.get('_line_number')}")

        target = self._normalize_target(row.get("target"))
        if target not in (0, 1):
            raise ValueError(f"Invalid target in input row at line {row.get('_line_number')}: {row.get('target')!r}")

        record: dict[str, Any] = {
            "function": func,
            "vulnerable": target,
            "cwe_id": self._resolve_cwe_id(row),
            "pair_id": pair_id,
        }

        project = self._first_non_empty(row.get("project"), None)
        if project is not None:
            record["project"] = project

        commit_id = self._first_non_empty(row.get("commit_id"), None)
        if commit_id is not None:
            record["commit_id"] = commit_id

        cve = self._first_non_empty(row.get("cve"), None)
        if cve is not None:
            record["cve_id"] = cve

        cve_description = self._first_non_empty(row.get("cve_description"), row.get("cve_desc"), None)
        if cve_description is not None:
            record["cve_description"] = cve_description

        diff = self._first_non_empty(row.get("diff"), None)
        if diff is not None:
            record["diff"] = diff

        idx = self._first_non_empty(row.get("idx"), None)
        if idx is not None:
            record["id"] = idx

        return record

    def _resolve_cwe_id(self, row: dict[str, Any]) -> list[str]:
        raw_value = self._first_non_empty(row.get("cwe_label"), row.get("cwe"), None)

        if isinstance(raw_value, list):
            cleaned = [str(item) for item in raw_value if item not in (None, "", "None")]
            return cleaned or ["CWE-UNKNOWN"]
        if raw_value in (None, "", "None"):
            return ["CWE-UNKNOWN"]
        return [str(raw_value)]

    def _write_json(self, path: Path, data: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")

    def _write_report(
        self,
        output_path: Path,
        input_path: Path,
        stats: AdapterStats,
        invalid_pair_examples: list[dict[str, Any]],
    ) -> None:
        report = {
            "input_file": str(input_path),
            "output_file": str(output_path),
            "total_input_rows": stats.total_input_rows,
            "converted_records": stats.converted_records,
            "invalid_pairs": stats.invalid_pairs,
            "fallback_cwe_ids": stats.fallback_cwe_ids,
            "strict_pairs": self.strict_pairs,
            "invalid_pair_examples": invalid_pair_examples,
        }
        report_path = output_path.with_name(output_path.stem + "_report.json")
        with report_path.open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)

    @staticmethod
    def _first_non_empty(*values: Any) -> Any:
        for value in values:
            if value not in (None, "", "None"):
                return value
        return None

    @staticmethod
    def _normalize_target(value: Any) -> int:
        if value in (0, 1):
            return int(value)
        if value in ("0", "1"):
            return int(value)
        raise ValueError(f"Invalid target value: {value!r}")

    @staticmethod
    def _normalize_comparable_value(value: Any) -> Any:
        if isinstance(value, list):
            return tuple(str(item) for item in value)
        return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert PrimeVul paired JSONL splits into SVD-Bench-compatible JSON files."
    )
    parser.add_argument(
        "--input-dir",
        default=str(DEFAULT_INPUT_DIR),
        help=f"Input PrimeVul directory (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output SVD-Bench directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=list(DEFAULT_SPLITS),
        choices=list(DEFAULT_SPLITS),
        help="Which splits to convert (default: train valid test)",
    )
    parser.add_argument(
        "--strict-pairs",
        action="store_true",
        help="Abort on the first invalid adjacent pair instead of skipping invalid pairs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    adapter = PrimeVulToSVDBenchAdapter(
        input_dir=Path(args.input_dir).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        strict_pairs=args.strict_pairs,
    )

    outputs = adapter.run(tuple(args.splits))
    print(f"✓ Converted {sum(len(v) for v in outputs.values())} total records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
