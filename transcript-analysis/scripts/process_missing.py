"""
process_missing.py — Generate tree files for transcripts that were skipped
due to encoding issues in the batch process.
"""

import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SOURCE_DIR = Path(r"C:\Projects\Dashboard\1. Capture\Better_Version")
CLEAN_DIR = SOURCE_DIR / "clean"
TREE_DIR = SOURCE_DIR / "trees"
SCRIPTS_DIR = Path(
    r"C:\Projects\Dashboard\6. Vault\Skill\transcript-analysis\scripts"
)
OUTPUT_DIR = Path(r"C:\Projects\Dashboard\4. Blueprint\Books")

sys.stdout.reconfigure(encoding="utf-8")

# Find all md files that DON'T have a corresponding tree file
all_md = sorted(SOURCE_DIR.glob("*_Fast.md"))
count_all = 0
count_ok = 0

for md_path in all_md:
    base_name = md_path.stem
    tree_path = TREE_DIR / f"{base_name}.tree.json"
    clean_path = CLEAN_DIR / f"{base_name}.txt"

    if tree_path.exists():
        continue  # already has tree

    count_all += 1
    print(f"\n[{count_all}] Processing: {base_name[:60]}...", flush=True)

    # Step 1.5: Preprocess
    if not clean_path.exists():
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS_DIR / "preprocess_transcript.py"),
                "--input",
                str(md_path),
                "--output",
                str(clean_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  PREPROCESS FAILED: {result.stderr[:200]}")
            continue
        if not clean_path.exists():
            print(f"  PREPROCESS FAILED (no output file)")
            continue
        print(f"  Preprocessed OK", flush=True)

    # Step 2: Content mapper
    video_title = base_name.replace("_Fast", "").replace("_", " ")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "content_mapper.py"),
            "--input",
            str(clean_path),
            "--source-type",
            "youtube",
            "--video-title",
            video_title,
            "--output",
            str(tree_path),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if tree_path.exists():
        tree_data = json.loads(tree_path.read_text(encoding="utf-8"))
        count_ok += 1
        print(
            f"  OK — {tree_data.get('estimated_leaf_nodes', 0)} leaves, "
            f"{tree_data.get('word_count', 0)} words",
            flush=True,
        )
    else:
        print(f"  MAPPER FAILED", flush=True)

print(f"\n{'='*60}")
print(f"Done: {count_ok}/{count_all} trees generated for previously missing files.")
