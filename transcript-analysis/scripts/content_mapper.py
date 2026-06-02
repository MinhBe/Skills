"""
content_mapper.py — Parse a transcript and suggest a concept tree.

Usage:
  python content_mapper.py --input transcript.txt --source-type youtube
  python content_mapper.py --input transcript.txt --source-type book --min-nodes 12
  python content_mapper.py          # demo mode — runs on built-in Deep Work excerpt

Outputs:
  - JSON concept tree to stdout (or --output file)
  - Human-readable tree summary
  - Minimum yield check (PASS/WARN)

The mapper is a heuristic assistant, not a decision-maker.
Claude reviews and adjusts the suggested tree before confirming with user.
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Force UTF-8 output on Windows consoles that default to cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Minimum yield guidance ──────────────────────────────────────────────────
MIN_YIELD = {
    "youtube": {"short": 3, "medium": 8, "long": 12},   # 10min / 30min / 45+min
    "book":    {"short": 5, "medium": 12, "long": 20},
    "article": {"short": 3, "medium": 5, "long": 8},
    "podcast": {"short": 3, "medium": 6, "long": 10},
    "other":   {"short": 3, "medium": 6, "long": 10},
}

# ── Heuristic patterns ───────────────────────────────────────────────────────
# Patterns that suggest a BRANCH (container of sub-concepts)
BRANCH_PATTERNS = [
    r"có\s+(\d+)\s+(loại|cách|bước|nguyên tắc|model|phương pháp|chiến lược|yếu tố|điều|lý do|dấu hiệu)",
    r"(\d+)\s+(types?|ways?|steps?|models?|methods?|strategies?|factors?|reasons?|principles?)",
    r"(first|second|third|fourth|fifth|thứ nhất|thứ hai|thứ ba|thứ tư|thứ năm)",
    r"(1\.|2\.|3\.|4\.|5\.)\s+\w",
    r"model\s+\d|phương pháp\s+\d",
]

# Patterns that suggest a LEAF (directly extractable idea)
LEAF_SIGNAL_PATTERNS = [
    r"(là gì|là một|được định nghĩa|có nghĩa là|refers to|is defined as|means that)",
    r"(vì sao|tại sao|why does|the reason|because)",
    r"(ví dụ|example|for instance|chẳng hạn|như là)",
    r"(nghiên cứu|study shows|theo.*cho thấy|according to|research)",
]

# Section break patterns
SECTION_BREAK = [
    r"^#{1,3}\s+",                   # markdown headers
    r"^[A-Z][A-Z\s]{4,}$",          # ALL CAPS lines
    r"^\s*---+\s*$",                  # horizontal rules
    r"^(Phần|Section|Chapter|Part)\s+\d",
]

# Max length for a line to qualify as a "standalone title" heuristic
_TITLE_MAX_LEN = 70

DEMO_TRANSCRIPT = """
Deep Work là gì?
Deep Work là khả năng tập trung hoàn toàn vào một công việc đòi hỏi nhận thức cao mà không bị phân tâm. Cal Newport định nghĩa đây là năng lực cốt lõi trong nền kinh tế tri thức.

Tại sao Deep Work quan trọng?
Trong nền kinh tế hiện đại, 3 nhóm người thành công nhất là: chuyên gia công nghệ cao, siêu sao trong lĩnh vực, và nhà đầu tư tư bản. Deep Work giúp bạn gia nhập một trong ba nhóm đó.

Myelin Hypothesis
Lặp đi lặp lại có chủ đích (deliberate practice) → tăng sản xuất myelin → kết nối thần kinh mạnh hơn → kỹ năng tốt hơn. Đây là cơ chế sinh học đằng sau Deep Work.

Có 4 Deep Work Models:
1. Monastic Model: Loại bỏ hoàn toàn mọi shallow obligation. Phù hợp với nhà văn, nhà toán học.
2. Bimodal Model: Chia thời gian rõ ràng — thời gian deep work và thời gian bình thường.
3. Rhythmic Model: Lên lịch deep work hàng ngày theo thói quen. Ví dụ: 6-7 giờ sáng mỗi ngày.
4. Journalist Model: Tập trung sâu bất cứ lúc nào, bất cứ ở đâu như một phóng viên deadline.

Chiến lược Time Blocking
Bảo vệ thời gian bằng cách block lịch cho deep work trước. Không ai được lên lịch vào các block này.

Chain Method (Jerry Seinfeld)
Đánh dấu lên lịch mỗi ngày bạn hoàn thành deep work. Mục tiêu: không phá chuỗi.

Rest Strategy
Não bình thường chỉ tập trung được tối đa 4 giờ mỗi ngày. Sau đó cần rest thực sự — không phải chuyển sang task khác. Tắt phone, không scroll, để não phục hồi hoàn toàn.

Shutdown Ritual
Trước khi kết thúc ngày làm việc: viết ra tất cả task chưa hoàn thành, lên kế hoạch ngày mai. Não sẽ ngừng "xử lý nền" và nghỉ ngơi thật sự.
"""


@dataclass
class ConceptNode:
    key: str
    label: str
    node_type: str          # "branch" or "leaf"
    depth: int
    section_hint: str = ""
    children: list = field(default_factory=list)

    def to_dict(self) -> dict:
        d = {
            "key": self.key,
            "label": self.label,
            "type": self.node_type,
            "depth": self.depth,
            "section": self.section_hint,
        }
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


def to_snake(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text[:60].strip("_")


def _is_standalone_title(lines: list[str], i: int) -> bool:
    """Heuristic: short line that starts a section (blank line before it or first line)."""
    line = lines[i].strip()
    if not line or len(line) > _TITLE_MAX_LEN:
        return False
    # Must be preceded by a blank line (or be the first non-empty line in the text)
    prev_blank = (i == 0) or (not lines[i - 1].strip())
    if not prev_blank:
        return False
    # Must be followed by a longer content line (confirms it is a heading, not isolated text)
    nxt = next((lines[j].strip() for j in range(i + 1, len(lines)) if lines[j].strip()), "")
    return bool(nxt) and len(nxt) > len(line)


def detect_sections(lines: list[str]) -> list[tuple[int, str]]:
    """Return list of (line_index, section_title) for detected section breaks."""
    sections = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        matched = False
        for pat in SECTION_BREAK:
            if re.match(pat, stripped):
                clean = re.sub(r"^#+\s*", "", stripped).strip()
                # Skip pure-separator lines (---, ===, etc.) and metadata lines
                if clean and not re.match(r"^[-=*#\s]+$", clean):
                    sections.append((i, clean))
                matched = True
                break
        if not matched and _is_standalone_title(lines, i):
            # Skip obvious metadata lines from FAST transcript headers
            if not re.match(r"^(\[FAST\]|[-*]\s*(Nguồn|Ngày|Ngôn ngữ))", stripped):
                sections.append((i, stripped))
    return sections


def count_branch_children(text: str) -> int:
    """Estimate how many sub-concepts a branch will have."""
    for pat in BRANCH_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except (IndexError, ValueError):
                return 2  # default if pattern matched but no number
    return 0


def build_tree(text: str, source_type: str) -> list[ConceptNode]:
    lines = text.strip().split("\n")
    sections = detect_sections(lines)
    nodes: list[ConceptNode] = []

    if not sections:
        # No section markers — treat whole transcript as one branch to split
        branch = ConceptNode(
            key="main_topic",
            label="Main Topic (no sections detected)",
            node_type="branch",
            depth=1,
            section_hint="full transcript"
        )
        nodes.append(branch)
        return nodes

    for idx, (line_i, title) in enumerate(sections):
        # Collect text of this section
        end = sections[idx + 1][0] if idx + 1 < len(sections) else len(lines)
        section_text = "\n".join(lines[line_i:end])
        n_children = count_branch_children(section_text)

        if n_children >= 2:
            # This is a BRANCH — create it + placeholder children
            branch = ConceptNode(
                key=to_snake(title),
                label=title,
                node_type="branch",
                depth=1,
                section_hint=f"line {line_i}"
            )
            for ci in range(n_children):
                child = ConceptNode(
                    key=f"{to_snake(title)}_item_{ci+1}",
                    label=f"[Item {ci+1} of {title} — label manually]",
                    node_type="leaf",
                    depth=2,
                    section_hint=f"sub-section {ci+1}"
                )
                branch.children.append(child)
            nodes.append(branch)
        else:
            # LEAF — directly extractable
            leaf = ConceptNode(
                key=to_snake(title),
                label=title,
                node_type="leaf",
                depth=1,
                section_hint=f"line {line_i}"
            )
            nodes.append(leaf)

    return nodes


def count_leaves(nodes: list[ConceptNode]) -> int:
    total = 0
    for n in nodes:
        if n.node_type == "leaf":
            total += 1
        total += count_leaves(n.children)
    return total


def yield_check(leaf_count: int, source_type: str, word_count: int) -> tuple[str, str]:
    mins = MIN_YIELD.get(source_type, MIN_YIELD["other"])
    if word_count < 500:
        minimum = mins["short"]
        tier = "short"
    elif word_count < 2000:
        minimum = mins["medium"]
        tier = "medium"
    else:
        minimum = mins["long"]
        tier = "long"

    if leaf_count >= minimum:
        return "PASS", f"{leaf_count} leaves >= {minimum} minimum ({source_type}/{tier})"
    else:
        return "WARN", f"{leaf_count} leaves < {minimum} minimum ({source_type}/{tier}) — review tree, may need more splits"


def print_tree(nodes: list[ConceptNode], indent: int = 0):
    for n in nodes:
        prefix = "  " * indent
        tag = "[BRANCH]" if n.node_type == "branch" else "[LEAF  ]"
        print(f"{prefix}{tag}  {n.label}  ({n.key})")
        if n.children:
            print_tree(n.children, indent + 1)


def parse_title_hint(title: str) -> tuple[int, str]:
    """Extract N and content_type from video titles like '4 bước X' or '3 sự thật về Y'.
    Returns (n_concepts, content_type_hint).
    """
    title_lower = title.lower()
    m = re.search(
        r"(\d+)\s+(loại|cách|bước|sự thật|nguyên tắc|phương pháp|chiến lược|"
        r"yếu tố|lý do|dấu hiệu|thói quen|kỹ năng|bài học|"
        r"types?|ways?|steps?|truths?|principles?|methods?|lessons?)",
        title_lower
    )
    if m:
        return int(m.group(1)), m.group(2)
    return 0, ""


def main():
    parser = argparse.ArgumentParser(description="Build concept tree from transcript")
    parser.add_argument("--input", help="Path to transcript text file")
    parser.add_argument("--source-type", default="youtube",
                        choices=["youtube", "book", "article", "podcast", "other"])
    parser.add_argument("--min-nodes", type=int, help="Override minimum leaf node count")
    parser.add_argument("--video-title", help="Video/source title — used to infer N concepts from '3 ways X' pattern")
    parser.add_argument("--output", help="Write JSON tree to file (default: stdout)")
    args = parser.parse_args()

    if args.input:
        path = Path(args.input)
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8")
    else:
        print("No --input provided. Running in DEMO MODE on Deep Work excerpt.\n")
        text = DEMO_TRANSCRIPT

    word_count = len(text.split())
    source_type = args.source_type

    # Title hint: parse N from "3 bước X" style titles
    title_n = 0
    title_hint = ""
    if args.video_title:
        title_n, title_hint = parse_title_hint(args.video_title)
        if title_n:
            print(f"  Title hint: '{args.video_title}' -- suggests {title_n} {title_hint} nodes")

    nodes = build_tree(text, source_type)
    leaf_count = count_leaves(nodes)

    # Yield check: title_n overrides word-count-based minimum if provided
    if args.min_nodes:
        minimum = args.min_nodes
        status = "PASS" if leaf_count >= minimum else "WARN"
        detail = f"{leaf_count} leaves {'>=': '<'[status=='WARN']} {minimum} (custom minimum)"
    elif title_n:
        status = "PASS" if leaf_count >= title_n else "WARN"
        detail = f"{leaf_count} leaves {'>=': '<'[status=='WARN']} {title_n} (from title: {title_n} {title_hint})"
    else:
        status, detail = yield_check(leaf_count, source_type, word_count)

    # Human-readable output
    print(f"{'='*60}")
    print(f"  CONTENT MAPPER  --  source_type: {source_type}")
    print(f"  words: {word_count}  |  leaf nodes found: {leaf_count}")
    print(f"  yield check: [{status}] {detail}")
    print(f"{'='*60}\n")
    print_tree(nodes)
    print()

    if status == "WARN":
        print("  [!] Fewer leaf nodes than expected.")
        print("     Review the tree above -- some BRANCH nodes may need further splitting.")
        print("     See references/granularity-guide.md for rules.\n")

    print("  Next: Review this tree with the user, adjust labels/splits, then confirm.")
    print("  After confirmation, proceed to per-leaf extraction (Step 4 in SKILL.md).\n")

    # JSON output
    result = {
        "source_type": source_type,
        "word_count": word_count,
        "estimated_leaf_nodes": leaf_count,
        "title_hint_n": title_n if title_n else None,
        "minimum_yield_check": f"{status}: {detail}",
        "tree": [n.to_dict() for n in nodes]
    }

    if args.output:
        out = Path(args.output)
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  JSON tree written to: {out}")
    else:
        print("  JSON tree:")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
