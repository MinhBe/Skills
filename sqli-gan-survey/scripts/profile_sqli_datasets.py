#!/usr/bin/env python3
"""Read-only profiler for the SQLi datasets used by sqli-gan-survey.

The script prints schema and quality stats. It does not transform datasets or
write training adapters.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


DEFAULT_MODIFIED = Path(
    r"D:\GAN_Final\Product\Dataset\Modified_SQL_Dataset\Modified_SQL_Dataset.csv"
)
DEFAULT_KAGGLE_DIR = Path(r"D:\GAN_Final\Product\Dataset\Kaggle_SQL_Injection_Dataset")
DEFAULT_KAGGLE_FILES = ("sqli.csv", "sqliv2.csv", "SQLiV3.csv")

TEXT_CANDIDATES = ("Query", "Sentence", "text", "payload", "Payload", "query")
LABEL_CANDIDATES = ("Label", "label", "Class", "class", "target", "Target")
VALID_LABELS = {"0", "1"}


def _detect_encoding(path: Path) -> str:
    sample = path.read_bytes()[:4096]
    if sample.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    if sample.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if b"\x00" in sample:
        even_nulls = sample[0::2].count(0)
        odd_nulls = sample[1::2].count(0)
        if odd_nulls > even_nulls:
            return "utf-16-le"
        if even_nulls > odd_nulls:
            return "utf-16-be"
    return "utf-8-sig"


def _open_csv(path: Path):
    return path.open("r", encoding=_detect_encoding(path), errors="replace", newline="")


def _clean(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _fieldnames(path: Path) -> List[str]:
    with _open_csv(path) as handle:
        reader = csv.reader(handle)
        try:
            row = next(reader)
        except StopIteration:
            return []
    return [_clean(item) for item in row]


def _pick_column(fieldnames: Iterable[str], candidates: Iterable[str]) -> Optional[str]:
    fields = list(fieldnames)
    lower_to_original = {field.lower(): field for field in fields if field}
    for candidate in candidates:
        if candidate in fields:
            return candidate
        found = lower_to_original.get(candidate.lower())
        if found:
            return found
    return None


def profile_csv(path: Path) -> Dict[str, object]:
    """Profile one CSV file without mutating it."""

    path = path.resolve()
    result: Dict[str, object] = {
        "path": str(path),
        "exists": path.exists(),
        "size_bytes": path.stat().st_size if path.exists() else 0,
    }
    if not path.exists():
        result["error"] = "file_not_found"
        return result

    fieldnames = _fieldnames(path)
    text_col = _pick_column(fieldnames, TEXT_CANDIDATES)
    label_col = _pick_column(fieldnames, LABEL_CANDIDATES)

    rows = 0
    empty_text = 0
    empty_label = 0
    invalid_label = 0
    malformed_rows = 0
    label_counts: Counter[str] = Counter()
    text_counts: Counter[str] = Counter()
    pair_counts: Counter[Tuple[str, str]] = Counter()

    with _open_csv(path) as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rows += 1
            if None in row:
                malformed_rows += 1

            text = _clean(row.get(text_col)) if text_col else ""
            label = _clean(row.get(label_col)) if label_col else ""
            label = label.strip("\"'")

            if not text:
                empty_text += 1
            else:
                text_counts[text] += 1

            if not label:
                empty_label += 1
            elif label not in VALID_LABELS:
                invalid_label += 1
            else:
                label_counts[label] += 1
                if text:
                    pair_counts[(text, label)] += 1

    duplicate_text_values = sum(1 for count in text_counts.values() if count > 1)
    duplicate_text_rows = sum(count - 1 for count in text_counts.values() if count > 1)
    duplicate_pair_values = sum(1 for count in pair_counts.values() if count > 1)
    duplicate_pair_rows = sum(count - 1 for count in pair_counts.values() if count > 1)

    result.update(
        {
            "columns": fieldnames,
            "text_column": text_col,
            "label_column": label_col,
            "rows": rows,
            "label_counts": dict(sorted(label_counts.items())),
            "empty_text": empty_text,
            "empty_label": empty_label,
            "invalid_label": invalid_label,
            "malformed_rows": malformed_rows,
            "duplicate_text_values": duplicate_text_values,
            "duplicate_text_rows": duplicate_text_rows,
            "duplicate_pair_values": duplicate_pair_values,
            "duplicate_pair_rows": duplicate_pair_rows,
        }
    )
    return result


def _default_paths(modified: Path, kaggle_dir: Path) -> List[Path]:
    return [modified] + [kaggle_dir / name for name in DEFAULT_KAGGLE_FILES]


def profile_all(modified: Path, kaggle_dir: Path, extra_files: List[Path]) -> Dict[str, object]:
    files = _default_paths(modified, kaggle_dir) + extra_files
    profiles = [profile_csv(path) for path in files]
    aggregate_labels: Counter[str] = Counter()
    aggregate_rows = 0
    for item in profiles:
        aggregate_rows += int(item.get("rows", 0) or 0)
        aggregate_labels.update(item.get("label_counts", {}))

    return {
        "mode": "read_only_dataset_profile",
        "files": profiles,
        "aggregate": {
            "rows": aggregate_rows,
            "valid_label_counts": dict(sorted(aggregate_labels.items())),
        },
    }


def print_markdown(report: Dict[str, object]) -> None:
    print("# SQLi Dataset Profile")
    print()
    print("Mode: read-only. No dataset conversion or training adapter was created.")
    print()
    print("| File | Text column | Label column | Rows | Labels | Empty text | Empty label | Invalid label | Malformed | Duplicate text rows |")
    print("|---|---|---|---:|---|---:|---:|---:|---:|---:|")
    for item in report["files"]:
        path = Path(str(item["path"]))
        labels = json.dumps(item.get("label_counts", {}), ensure_ascii=True)
        print(
            "| {file} | {text} | {label} | {rows} | {labels} | {empty_text} | "
            "{empty_label} | {invalid_label} | {malformed} | {dupes} |".format(
                file=path.name,
                text=item.get("text_column") or "",
                label=item.get("label_column") or "",
                rows=item.get("rows", 0),
                labels=labels,
                empty_text=item.get("empty_text", 0),
                empty_label=item.get("empty_label", 0),
                invalid_label=item.get("invalid_label", 0),
                malformed=item.get("malformed_rows", 0),
                dupes=item.get("duplicate_text_rows", 0),
            )
        )
    print()
    print("Aggregate valid labels:")
    print(json.dumps(report["aggregate"]["valid_label_counts"], indent=2, ensure_ascii=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile SQLi CSV datasets without modifying them.")
    parser.add_argument("--modified", type=Path, default=DEFAULT_MODIFIED)
    parser.add_argument("--kaggle-dir", type=Path, default=DEFAULT_KAGGLE_DIR)
    parser.add_argument("--extra-file", type=Path, action="append", default=[])
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = profile_all(args.modified, args.kaggle_dir, args.extra_file)
    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print_markdown(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
