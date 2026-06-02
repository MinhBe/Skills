"""
batch_process.py — Batch process all Better_Version transcripts through the
transcript-analysis pipeline: preprocess → content_mapper → aggregated dossier.

Usage:
  python scripts/batch_process.py

Output:
  - C:\Projects\Dashboard\4. Blueprint\Books\Better_Version_Master_Dossier.md
  - C:\Projects\Dashboard\4. Blueprint\Books\Better_Version_Summary.json
  - Clean files: ...\Better_Version\clean\
  - Tree files: ...\Better_Version\trees\
"""

import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SOURCE_DIR = Path(r"C:\Projects\Dashboard\1. Capture\Better_Version")
CLEAN_DIR = SOURCE_DIR / "clean"
TREE_DIR = SOURCE_DIR / "trees"
OUTPUT_DIR = Path(r"C:\Projects\Dashboard\4. Blueprint\Books")
SKILL_DIR = Path(r"C:\Projects\Dashboard\6. Vault\Skill\transcript-analysis")
SCRIPTS_DIR = SKILL_DIR / "scripts"

CLEAN_DIR.mkdir(parents=True, exist_ok=True)
TREE_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.stdout.reconfigure(encoding="utf-8")


def run_python(script: str, *args: str) -> tuple[str, str, int]:
    cmd = [sys.executable, str(SCRIPTS_DIR / script)] + list(args)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return proc.stdout, proc.stderr, proc.returncode


def extract_book_name(base_name: str) -> str:
    m = re.search(r'S[áa]ch\s+(.+?)(?:_Fast|$)', base_name)
    if m:
        return m.group(1).strip()
    return ""


def extract_video_title(base_name: str) -> str:
    name = base_name.replace("_Fast", "").replace("_", " ")
    return name


def build_dossier(results: list[dict]) -> str:
    lines = []

    def w(s: str = ""):
        lines.append(s)

    total_words = sum(r["word_count"] for r in results)
    total_leaves = sum(r["leaf_count"] for r in results)
    avg_leaves = round(total_leaves / len(results), 1) if results else 0
    avg_words = round(total_words / len(results), 0) if results else 0

    yield_stats: dict[str, int] = {}
    for r in results:
        key = r["yield_check"].split(":")[0].strip()
        yield_stats[key] = yield_stats.get(key, 0) + 1

    w("# Master Learning Dossier — Better Version Library")
    w()
    w(f"**Domain:** book")
    w(f"**Source type:** youtube")
    w(f"**Channel:** Better Version")
    w(f"**Total sources processed:** {len(results)}")
    w(f"**Extracted:** {datetime.now().strftime('%Y-%m-%d')}")
    w()
    w("---")
    w()
    w("## Tổng quan")
    w()
    w("Better Version là kênh YouTube chia sẻ kiến thức phát triển bản thân toàn diện qua các cuốn sách hay, do một người Việt Nam thực hiện. Kênh tập trung vào tóm tắt và phân tích các cuốn sách thuộc nhiều lĩnh vực: phát triển bản thân, tâm lý học, triết học, tài chính cá nhân, khoa học, văn học và sức khỏe. Các video được trình bày dưới dạng transcript chi tiết bằng tiếng Việt, phù hợp cho người Việt muốn tiếp cận tri thức từ sách quốc tế.")
    w()
    w(f"Better Version là kênh YouTube tóm tắt sách về đa lĩnh vực. Luận điểm cốt lõi là việc đọc và hiểu các cuốn sách hay sẽ giúp phát triển toàn diện bản thân trên mọi phương diện. Dossier này cover {len(results)} transcripts, trọng tâm là kỹ năng tư duy, tâm lý học ứng dụng, và phát triển bản thân. Sau khi học, bạn có thể áp dụng kiến thức từ nhiều lĩnh vực khác nhau vào cuộc sống và công việc hàng ngày.")
    w()
    w("---")
    w()
    w("## Mục lục theo sách")
    w()

    # Group by book name
    book_groups: dict[str, list] = {}
    for r in results:
        bn = r["book_name"] or "Không xác định"
        book_groups.setdefault(bn, []).append(r)

    for book_name, items in sorted(book_groups.items()):
        w(f"### {book_name}")
        w()
        for i, item in enumerate(items, 1):
            w(f"{i}. **{item['base_name']}** — {item['word_count']} từ, {item['leaf_count']} concepts _({item['yield_check']})_")
        w()

    w("---")
    w()
    w("## Thống kê tổng hợp")
    w()
    w("| Metric | Value |")
    w("|---|---|")
    w(f"| Tổng số transcript | {len(results)} |")
    w(f"| Tổng số từ (word count) | {total_words} |")
    w(f"| Tổng số leaf nodes | {total_leaves} |")
    w(f"| Trung bình leaves/video | {avg_leaves} |")
    w(f"| Trung bình từ/video | {avg_words} |")
    w()
    w("### Phân phối Yield Check")
    w()
    for status, count in sorted(yield_stats.items()):
        pct = round(count / len(results) * 100, 1) if results else 0
        w(f"- **{status}**: {count} files ({pct}%)")
    w()
    w("---")
    w()
    w("## Danh sách đầy đủ (chi tiết từng transcript)")
    w()

    for idx, r in enumerate(results, 1):
        tree_path = Path(r["tree_path"])
        tree_preview = "(no tree data)"
        if tree_path.exists():
            try:
                tree_data = json.loads(tree_path.read_text(encoding="utf-8"))
                tree_preview = json.dumps(tree_data, ensure_ascii=False)
            except (json.JSONDecodeError, Exception):
                pass

        w(f"### {idx}. {r['base_name']}")
        w()
        w("| Field | Value |")
        w("|---|---|")
        w(f"| Sách | {r['book_name']} |")
        w(f"| Word count | {r['word_count']} |")
        w(f"| Leaf nodes | {r['leaf_count']} |")
        w(f"| Yield | {r['yield_check']} |")
        w()
        w("**Concept tree:**")
        w("```")
        w(tree_preview)
        w("```")
        w()
        w("---")
        w()

    w("---")
    w(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} by transcript-analysis skill*")

    return "\n".join(lines)


def main():
    md_files = sorted(glob.glob(str(SOURCE_DIR / "*_Fast.md")))
    total = len(md_files)
    results = []

    print(f"Found {total} files to process.\n")

    for i, filepath in enumerate(md_files, 1):
        filepath = Path(filepath)
        base_name = filepath.stem
        clean_file = CLEAN_DIR / f"{base_name}.txt"
        tree_file = TREE_DIR / f"{base_name}.tree.json"

        print(f"[{i}/{total}] {base_name}...", end=" ", flush=True)

        # Clean base name
        base_name_clean = base_name.replace("_Fast", "")

        # Step 1.5: Preprocess
        stdout, stderr, rc = run_python(
            "preprocess_transcript.py",
            "--input", str(filepath),
            "--output", str(clean_file),
        )
        if rc != 0 or not clean_file.exists():
            print(f"PREPROCESS FAILED: {stderr.strip()}")
            continue

        # Step 2: Content mapper
        video_title = extract_video_title(base_name)
        stdout, stderr, rc = run_python(
            "content_mapper.py",
            "--input", str(clean_file),
            "--source-type", "youtube",
            "--video-title", video_title,
            "--output", str(tree_file),
        )
        if rc != 0 or not tree_file.exists():
            print(f"MAPPER FAILED: {stderr.strip()}")
            continue

        # Parse tree JSON
        try:
            tree_content = json.loads(tree_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"INVALID JSON: {e}")
            continue

        book_name = extract_book_name(base_name)

        results.append({
            "file_name": filepath.name,
            "base_name": base_name_clean,
            "book_name": book_name,
            "word_count": tree_content.get("word_count", 0),
            "leaf_count": tree_content.get("estimated_leaf_nodes", 0),
            "yield_check": tree_content.get("minimum_yield_check", "?"),
            "tree_path": str(tree_file),
        })

        print(f"OK — {tree_content.get('estimated_leaf_nodes', 0)} leaves, {tree_content.get('word_count', 0)} words")

    # Generate dossier
    print(f"\n{'='*60}")
    print(f"Processing complete: {len(results)} / {total} files succeeded.")
    print(f"\nGenerating master dossier...")

    dossier = build_dossier(results)
    dossier_path = OUTPUT_DIR / "Better_Version_Master_Dossier.md"
    dossier_path.write_text(dossier, encoding="utf-8")
    print(f"  Dossier written to: {dossier_path}")

    # Write summary JSON
    summary_path = OUTPUT_DIR / "Better_Version_Summary.json"
    summary_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  Summary JSON: {summary_path}")

    # Stats
    total_words = sum(r["word_count"] for r in results)
    total_leaves = sum(r["leaf_count"] for r in results)
    yield_stats: dict[str, int] = {}
    for r in results:
        key = r["yield_check"].split(":")[0].strip()
        yield_stats[key] = yield_stats.get(key, 0) + 1

    print(f"\n=== FINAL STATS ===")
    print(f"  Files processed: {len(results)} / {total}")
    print(f"  Total words: {total_words}")
    print(f"  Total leaf nodes: {total_leaves}")
    print(f"  Yield distribution: {yield_stats}")
    print(f"\nDone. Output in: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
