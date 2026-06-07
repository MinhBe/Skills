from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return max(0, sum(1 for _ in handle) - 1)


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check SQLi GAN full-run acceptance artifacts.")
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--expected-rows", required=True, type=int)
    parser.add_argument("--expected-clones", type=int, default=18)
    parser.add_argument("--expect-waf", action="store_true")
    args = parser.parse_args()

    root = args.run_root
    expected_rows = args.expected_rows
    expected_clones = args.expected_clones

    clone_matrix = read_csv_rows(root / "reports" / "clone_status_matrix.csv")
    if len(clone_matrix) != expected_clones:
        fail(f"clone matrix rows {len(clone_matrix)} != {expected_clones}")
    bad_clones = [
        (row.get("method"), row.get("clone_name"), row.get("run_status"), row.get("generated_rows"))
        for row in clone_matrix
        if row.get("run_status") != "passed_generated" or int(row.get("generated_rows") or 0) != expected_rows
    ]
    if bad_clones:
        fail(f"clone matrix has non-accepted rows: {bad_clones[:5]}")

    metrics = read_csv_rows(root / "reports" / "metrics_summary.csv")
    if len(metrics) != expected_clones:
        fail(f"metrics rows {len(metrics)} != {expected_clones}")
    bad_metrics = [
        (
            row.get("method"),
            row.get("clone_name"),
            row.get("row_count"),
            row.get("prefix_coverage"),
            row.get("jsonl_raw_audit_coverage"),
        )
        for row in metrics
        if int(row.get("row_count") or 0) != expected_rows
        or float(row.get("prefix_coverage") or 0) != 1.0
        or float(row.get("jsonl_raw_audit_coverage") or 0) != 1.0
    ]
    if bad_metrics:
        fail(f"metrics summary has non-accepted rows: {bad_metrics[:5]}")

    result: dict[str, Any] = {
        "status": "passed",
        "run_root": str(root),
        "expected_rows": expected_rows,
        "clone_rows": len(clone_matrix),
        "metrics_rows": len(metrics),
    }

    if args.expect_waf:
        expected_waf_rows = expected_clones * expected_rows
        waf_input_rows = count_csv_rows(root / "waf" / "modsecurity_input_payloads.csv")
        if waf_input_rows != expected_waf_rows:
            fail(f"WAF input rows {waf_input_rows} != {expected_waf_rows}")

        code_summary = read_csv_rows(root / "waf" / "modsecurity_code_summary.csv")
        if len(code_summary) != expected_clones:
            fail(f"WAF code summary rows {len(code_summary)} != {expected_clones}")
        bad_code_rows = [
            (row.get("method"), row.get("clone_name"))
            for row in code_summary
            if int(row.get("input_rows") or 0) != expected_rows
            or int(row.get("blocked_count") or 0)
            + int(row.get("bypass_count") or 0)
            + int(row.get("error_count") or 0)
            != int(row.get("input_rows") or 0)
        ]
        if bad_code_rows:
            fail(f"WAF code summary has invalid rows: {bad_code_rows[:5]}")

        manifest_path = root / "waf" / "modsecurity_benchmark_manifest.json"
        if not manifest_path.exists():
            fail(f"missing WAF manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "completed":
            fail(f"WAF manifest status is {manifest.get('status')!r}, expected completed")
        result.update(
            {
                "waf_input_rows": waf_input_rows,
                "waf_code_summary_rows": len(code_summary),
                "waf_status": manifest.get("status"),
            }
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
