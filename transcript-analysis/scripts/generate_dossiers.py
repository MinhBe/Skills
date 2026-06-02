"""
generate_dossiers.py — Generate per-video Learning Dossier markdown files
following the dossier-template.md format from the transcript-analysis skill.

For each transcript with a matching tree JSON, this script:
1. Reads the cleaned transcript text
2. Reads the concept tree JSON
3. Generates a full Learning Dossier markdown file
4. Writes it to the Books output directory

Usage:
  python scripts/generate_dossiers.py
"""

import glob
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

SOURCE_DIR = Path(r"C:\Projects\Dashboard\1. Capture\Better_Version")
CLEAN_DIR = SOURCE_DIR / "clean"
TREE_DIR = SOURCE_DIR / "trees"
OUTPUT_DIR = Path(r"C:\Projects\Dashboard\4. Blueprint\Books")
SKILL_DIR = Path(r"C:\Projects\Dashboard\6. Vault\Skill\transcript-analysis")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

sys.stdout.reconfigure(encoding="utf-8")


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text[:80].strip("-")


def extract_book_name(base_name: str) -> str:
    m = re.search(r'S[áa]ch\s+(.+?)(?:_Fast|$)', base_name)
    if m:
        return m.group(1).strip()
    return ""


def extract_video_title(base_name: str) -> str:
    name = base_name.replace("_Fast", "").replace("_", " ")
    return name.strip()


def parse_tree(tree_path: Path) -> Optional[dict]:
    try:
        return json.loads(tree_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def get_source_text(clean_path: Path, md_path: Path) -> str:
    """Try clean text first, then fall back to raw markdown."""
    if clean_path.exists():
        text = clean_path.read_text(encoding="utf-8")
        if len(text.split()) > 50:
            return text
    if md_path.exists():
        content = md_path.read_text(encoding="utf-8")
        # Strip header/metadata, keep content from first timestamp onward
        lines = content.split("\n")
        content_lines = []
        started = False
        for line in lines:
            if re.match(r"^\[\d+:\d+\]", line.strip()):
                started = True
            if started:
                content_lines.append(line)
        return "\n".join(content_lines)
    return ""


def extract_section_text(transcript: str, section_hint: str) -> str:
    """Extract text around a section hint (line number or keyword)."""
    lines = transcript.split("\n")
    if section_hint.startswith("line "):
        try:
            line_idx = int(section_hint.replace("line ", ""))
            start = max(0, line_idx - 1)
            end = min(len(lines), line_idx + 10)
            return "\n".join(lines[start:end])
        except ValueError:
            pass
    # Fallback: search for keyword
    for i, line in enumerate(lines):
        if section_hint.lower() in line.lower():
            start = max(0, i - 1)
            end = min(len(lines), i + 8)
            return "\n".join(lines[start:end])
    return transcript[:500]


def build_tree_ascii(tree_data: dict) -> str:
    """Build an ASCII representation of the concept tree."""
    nodes = tree_data.get("tree", [])
    lines = []
    for node in nodes:
        indent = "  " * (node.get("depth", 1) - 1)
        tag = "[BRANCH]" if node.get("type") == "branch" else "[LEAF]"
        label = node.get("label", "?")
        key = node.get("key", "")
        lines.append(f"{indent}{tag}  {label}  ({key})")
        for child in node.get("children", []):
            c_indent = "  " * (child.get("depth", 2) - 1)
            c_tag = "[BRANCH]" if child.get("type") == "branch" else "[LEAF]"
            c_label = child.get("label", "?")
            c_key = child.get("key", "")
            lines.append(f"{c_indent}{c_tag}  {c_label}  ({c_key})")
    return "\n".join(lines)


def build_table_of_contents(tree_data: dict) -> list[str]:
    """Build table of contents from leaf nodes."""
    toc = []
    idx = 0
    for node in tree_data.get("tree", []):
        if node.get("type") == "leaf":
            idx += 1
            label = node.get("label", "?")
            key = node.get("key", "")
            toc.append(f"{idx}. **{key}** — {label} _(understand)_")
        for child in node.get("children", []):
            if child.get("type") == "leaf":
                idx += 1
                c_label = child.get("label", "?")
                c_key = child.get("key", "")
                toc.append(f"{idx}. **{c_key}** — {c_label} _(remember)_")
    if not toc:
        toc = ["1. *(No leaf nodes identified — tree needs refinement)*"]
    return toc


def estimate_source_type(source_type: str, word_count: int) -> tuple[str, str, int]:
    tier = "medium"
    if word_count < 500:
        tier = "short"
    elif word_count >= 2000:
        tier = "long"
    mins = {"youtube": {"short": 3, "medium": 8, "long": 12}}
    minimum = mins.get(source_type, mins["youtube"]).get(tier, 8)
    return source_type, tier, minimum


def get_yield_check(leaf_count: int, source_type: str, word_count: int) -> str:
    _, tier, minimum = estimate_source_type(source_type, word_count)
    if leaf_count >= minimum:
        return f"PASS: {leaf_count} leaves >= {minimum} minimum ({source_type}/{tier})"
    return f"WARN: {leaf_count} leaves < {minimum} minimum ({source_type}/{tier})"


def sanitize_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:120]


def generate_dossier(base_name: str, md_file: Path) -> Optional[str]:
    """Generate a Learning Dossier markdown for one video file."""
    base_name_clean = base_name.replace("_Fast", "")
    clean_file = CLEAN_DIR / f"{base_name}.txt"
    tree_file = TREE_DIR / f"{base_name}.tree.json"

    tree_data = parse_tree(tree_file)
    if not tree_data:
        return None

    transcript = get_source_text(clean_file, md_file)
    word_count = tree_data.get("word_count", len(transcript.split()))
    leaf_count = tree_data.get("estimated_leaf_nodes", 0)
    source_type = tree_data.get("source_type", "youtube")
    yield_check = tree_data.get("minimum_yield_check", get_yield_check(leaf_count, source_type, word_count))
    video_title = extract_video_title(base_name)
    book_name = extract_book_name(base_name)
    title_hint = tree_data.get("title_hint_n")

    # Determine backbone nodes (first few leaves at depth 1)
    all_leaves = [n for n in tree_data.get("tree", []) if n.get("type") == "leaf"]
    backbone = [n.get("key", "?") for n in all_leaves[:3]]

    today = datetime.now().strftime("%Y-%m-%d")

    lines = []
    def w(s=""):
        lines.append(s)

    # ── Header ──
    w(f"# Learning Dossier — {video_title}")
    w()
    w(f"**Domain:** book")
    w(f"**Source type:** {source_type}")
    w(f"**Source:** Better Version (YouTube)")
    w(f"**Book:** {book_name if book_name else 'N/A'}")
    w(f"**Extracted:** {today}")
    w(f"**Total nodes:** {leaf_count} leaves")
    w()
    w("---")
    w()

    # ── Tổng hợp ──
    w("## Tổng hợp")
    w()

    # Parse video title for topic clues
    topic_guess = book_name if book_name else video_title
    # Check for specific content patterns
    has_psychology = any(kw in video_title.lower() for kw in ["tâm lý", "cảm xúc", "hạnh phúc", "tình yêu"])
    has_finance = any(kw in video_title.lower() for kw in ["tiền", "tài chính", "giàu", "nghèo"])
    has_philosophy = any(kw in video_title.lower() for kw in ["triết", "đạo phật", "thiền", "tỉnh thức"])
    has_health = any(kw in video_title.lower() for kw in ["sức khoẻ", "sức khỏe", "cơ thể", "chữa lành"])
    has_self_dev = any(kw in video_title.lower() for kw in ["thói quen", "kỷ luật", "phát triển", "thành công", "tư duy"])

    domain_hint = "phát triển bản thân"
    if has_psychology: domain_hint = "tâm lý học"
    elif has_finance: domain_hint = "tài chính cá nhân"
    elif has_philosophy: domain_hint = "triết học và tâm linh"
    elif has_health: domain_hint = "sức khỏe và chữa lành"
    elif has_self_dev: domain_hint = "phát triển bản thân"

    w(f"Video này thuộc kênh Better Version, kênh YouTube chia sẻ kiến thức phát triển bản thân toàn diện qua các cuốn sách hay. Nội dung xoay quanh lĩnh vực {domain_hint}, được trình bày dưới dạng transcript tiếng Việt chi tiết, phù hợp cho người Việt muốn tiếp cận tri thức từ sách quốc tế.")
    w()

    w(f"{video_title} là video tóm tắt sách về {topic_guess} từ kênh Better Version. Luận điểm cốt lõi là việc áp dụng các nguyên lý từ cuốn sách này sẽ giúp người xem {domain_hint} một cách hiệu quả. Dossier này cover {leaf_count} concepts, trọng tâm là {', '.join(backbone[:3])}. Sau khi học, bạn có thể áp dụng các bài học từ video vào cuộc sống và công việc hàng ngày.")
    w()
    w("---")
    w()

    # ── Mục lục ──
    w("## Mục lục")
    w()
    toc = build_table_of_contents(tree_data)
    for item in toc:
        w(item)
    w()
    w("---")
    w()

    # ── Concept Tree ──
    w("## Concept Tree")
    w()
    w("```")
    w(build_tree_ascii(tree_data))
    w("```")
    w()
    w("---")
    w()

    # ── Per-Node Analysis ──
    w("## Phân tích chi tiết từng khái niệm")
    w()

    for i, node in enumerate(tree_data.get("tree", []), 1):
        node_type = node.get("type", "leaf")
        node_label = node.get("label", "?")
        node_key = node.get("key", "?")
        depth = node.get("depth", 1)
        section = node.get("section", "")

        section_text = extract_section_text(transcript, section)

        w(f"### {i}. {node_label} · depth {depth}")
        w()
        w(f"**Key:** `{node_key}`")
        w(f"**Type:** {node_type.upper()}")
        w(f"**Section:** {section}")
        w()

        if node_type == "branch":
            w(f"**Phân nhánh:** Khái niệm này chứa {len(node.get('children', []))} sub-concepts bên dưới.")
            w()
            for ci, child in enumerate(node.get("children", []), 1):
                child_key = child.get("key", "?")
                child_label = child.get("label", "?")
                child_section = child.get("section", "")
                child_text = extract_section_text(transcript, child_section)
                w(f"**{ci}. {child_label}** (`{child_key}`)")
                w()
                w(f"**Core question:** Ý chính của phần này trong transcript là gì?")
                w()
                w(f"**Extracted:**")
                w(f"```")
                w(child_text[:500] if child_text else "*Chưa có transcript để trích xuất*")
                w(f"```")
                w()
                w("**Three-tier explanation:**")
                w()
                w("**Child (analogy):** *Cần phân tích thêm*")
                w()
                w("**Student (mechanism):** *Cần phân tích thêm*")
                w()
                w("**Expert (trade-offs):** *Cần phân tích thêm*")
                w()
                w("**Misconception seeds:**")
                w("- *Cần phân tích thêm*")
                w("- *Cần phân tích thêm*")
                w()
                w("**Transfer question:** *Cần phân tích thêm*")
                w()
                w("---")
                w()
        else:
            w("**Core question:**")
            w(f"> Ý chính được rút ra từ phần transcript: \"{section_text[:150].strip()}...\"")
            w()
            w("**Extracted:**")
            w("```")
            w(section_text[:600] if section_text else "*Chưa có transcript để trích xuất*")
            w("```")
            w()
            w("**Anchor story:**")
            w("*Cần phân tích thêm từ transcript*")
            w()
            w("**Falsifiability:**")
            w("*Cần phân tích thêm*")
            w()
            w("**Three-tier explanation:**")
            w()
            w("**Child (analogy):**")
            w("*Cần phân tích thêm*")
            w()
            w("**Student (mechanism):**")
            w("*Cần phân tích thêm*")
            w()
            w("**Expert (trade-offs):**")
            w("*Cần phân tích thêm*")
            w()
            w("**Misconception seeds:**")
            w("- *Cần phân tích thêm*")
            w("- *Cần phân tích thêm*")
            w()
            w("**Transfer question:**")
            w("*Cần phân tích thêm*")
            w()
            w("**Dig deeper:**")
            w()
            w("| Level | Question |")
            w("|---|---|")
            w("| Apply | *Cần phân tích thêm* |")
            w("| Analyze | *Cần phân tích thêm* |")
            w("| Evaluate | *Cần phân tích thêm* |")
            w("| Create | *Cần phân tích thêm* |")
            w()
            w("**Next actions:**")
            w("1. *Cần phân tích thêm*")
            w("2. *Cần phân tích thêm*")
            w()
        w("---")
        w()

    # ── Yield Summary ──
    w("## Yield Summary")
    w()
    _, tier, minimum = estimate_source_type(source_type, word_count)
    w("| Check | Value |")
    w("|---|---|")
    w(f"| Source type | {source_type} |")
    w(f"| Word count | {word_count} |")
    w(f"| Tier | {tier} |")
    w(f"| Minimum required | {minimum} |")
    w(f"| Actual leaf nodes | {leaf_count} |")
    w(f"| Status | {yield_check} |")
    w()
    w("---")
    w()

    # ── Next Steps ──
    w("## Next Steps")
    w()
    w("- [ ] Review tree structure with human expert — adjust labels and confirm branch/leaf classification")
    w("- [ ] Run full per-leaf extraction (Step 3 in SKILL.md) for each node above")
    w("- [ ] Run `python scripts/validate_node.py` when nodes are extracted")
    w("- [ ] Run `python scripts/write_node.py --domain book --concept {key} --node {key}.json`")
    w("- [ ] Map cross-node relations once extraction is complete")
    w()

    w("---")
    w(f"*Generated on {today} by transcript-analysis skill — Better Version Library*")

    return "\n".join(lines)


def main():
    md_files = sorted(glob.glob(str(SOURCE_DIR / "*_Fast.md")))
    total = len(md_files)
    success = 0
    skipped = 0

    print(f"Found {total} transcript files.\n")

    for i, filepath in enumerate(md_files, 1):
        filepath = Path(filepath)
        base_name = filepath.stem

        tree_file = TREE_DIR / f"{base_name}.tree.json"
        if not tree_file.exists():
            skipped += 1
            print(f"[{i}/{total}] SKIP (no tree) — {base_name}")
            continue

        # Generate dossier
        dossier = generate_dossier(base_name, filepath)
        if dossier is None:
            skipped += 1
            print(f"[{i}/{total}] FAIL — {base_name}")
            continue

        # Write output
        video_title = extract_video_title(base_name)
        safe_name = sanitize_filename(video_title)
        out_path = OUTPUT_DIR / f"{safe_name}.md"

        # Avoid name collisions
        counter = 1
        while out_path.exists():
            out_path = OUTPUT_DIR / f"{safe_name}_{counter}.md"
            counter += 1

        out_path.write_text(dossier, encoding="utf-8")
        success += 1
        print(f"[{i}/{total}] OK — {base_name} -> {out_path.name}")

    print(f"\n{'='*60}")
    print(f"Done. Generated: {success} dossiers | Skipped: {skipped} | Total: {total}")
    print(f"Output directory: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
