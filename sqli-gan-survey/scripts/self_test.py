#!/usr/bin/env python3
"""Self-test for the sqli-gan-survey skill resources."""

from __future__ import annotations

import csv
import importlib.util
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_profiler():
    profiler_path = ROOT / "scripts" / "profile_sqli_datasets.py"
    spec = importlib.util.spec_from_file_location("profile_sqli_datasets", profiler_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load profile_sqli_datasets.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_required_files() -> None:
    required = [
        ROOT / "SKILL.md",
        ROOT / "references" / "model-scan-checklist.md",
        ROOT / "references" / "survey-report-template.md",
        ROOT / "scripts" / "profile_sqli_datasets.py",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise AssertionError(f"missing required files: {missing}")

    skill_text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for needle in ("sqli-gan-survey", "Minimal-Change Improvement Policy", "Dataset Profiling"):
        if needle not in skill_text:
            raise AssertionError(f"SKILL.md missing expected text: {needle}")


def test_profiler_sample() -> None:
    profiler = _load_profiler()
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        modified = tmp_path / "Modified_SQL_Dataset.csv"
        kaggle = tmp_path / "kaggle"
        kaggle.mkdir()
        sqli = kaggle / "sqli.csv"
        sqliv2 = kaggle / "sqliv2.csv"
        sqliv3 = kaggle / "SQLiV3.csv"

        with modified.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Query", "Label"])
            writer.writerow(["select * from users", "0"])
            writer.writerow(["' or 1=1 --", "1"])

        for path in (sqli, sqliv2, sqliv3):
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["Sentence", "Label"])
                writer.writerow(["normal input", "0"])
                writer.writerow(["admin'--", "1"])
                writer.writerow(["", "1"])

        report = profiler.profile_all(modified, kaggle, [])
        if report["aggregate"]["rows"] != 11:
            raise AssertionError(f"unexpected aggregate rows: {report['aggregate']['rows']}")
        labels = report["aggregate"]["valid_label_counts"]
        if labels != {"0": 4, "1": 7}:
            raise AssertionError(f"unexpected label counts: {labels}")
        if not all(item["text_column"] in ("Query", "Sentence") for item in report["files"]):
            raise AssertionError("profiler did not infer text columns")


def main() -> int:
    test_required_files()
    test_profiler_sample()
    print("sqli-gan-survey self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
