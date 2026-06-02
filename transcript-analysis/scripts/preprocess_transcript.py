"""
preprocess_transcript.py — Clean ASR transcripts before content mapping.

Usage:
  python preprocess_transcript.py --input transcript.txt
  python preprocess_transcript.py --input transcript.txt --output clean.txt
  python preprocess_transcript.py --demo       # runs on built-in Deep Work ASR excerpt

Purpose:
  ASR (speech recognition) transcripts from YouTube have format:
    [00:00] Short sentence fragment.
    [00:02] More words.
  This breaks content_mapper.py because:
    - No blank lines between lines → standalone title heuristic fires on 0 lines
    - Timestamps are noise
    - Short fragmented lines don't preserve semantic paragraph structure

  This script:
    1. Strips [MM:SS] timestamps
    2. Merges fragmented lines into semantic paragraphs
    3. Inserts blank lines at detected topic boundaries
    4. Outputs clean text that content_mapper can process

  After this script: run content_mapper.py on the output file.
"""

import argparse
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Topic pivot signals in Vietnamese YouTube ─────────────────────────────────
# These phrases at the start of a sentence signal a new topic or section.
PIVOT_PATTERNS = [
    # Explicit number/enumeration starts
    r"^(có\s+\d+|thứ\s+(nhất|hai|ba|bốn|năm|sáu|bảy|tám|chín|mười))",
    r"^(đầu tiên|tiếp theo|thứ ba|thứ tư|cuối cùng)",
    r"^(first|second|third|fourth|finally)[,\s]",
    r"^\d+\.\s+\w",
    # Rhetorical question pivots (common in Vietnamese YouTube)
    r"^vậy[,\s]",
    r"^vậy thì[,\s]",
    r"^vậy làm thế nào",
    r"^vậy tại sao",
    r"^nhưng tại sao",
    r"^tại sao",
    r"^vậy[,\s].*\?",
    # Named concept introductions
    r"^(khái niệm|phương pháp|mô hình|chiến lược|nguyên tắc|bước)\s+",
    r"^(concept|model|method|strategy|principle|step)\s+",
    # Definition signals
    r".+(là gì\?|là gì\s*$)",
    r"^(deep work|shallow work|flow|time block|chain method)",
    r"^\w[\w\s]{2,20}\s+là\s+(một|khả năng|trạng thái|phương pháp|khái niệm)",
    # Explicit section transitions
    r"^(vậy|thế|và)\s+.{0,20}(tiếp theo|sau đây|bây giờ|chúng ta)",
    r"^(ngoài ra|bên cạnh đó|không chỉ vậy|hơn nữa)[,\s]",
    r"^(điều\s+(thứ|tiếp theo|quan trọng|cuối cùng))",
    r"^(cách|bước)\s+\d+",
    # Book/source citation (signals new concept with external support)
    r"^trong\s+(cuốn sách|nghiên cứu|một nghiên cứu)",
    r"^(according to|in the book|research shows)",
]

# Lines longer than this (in chars, after stripping timestamp) are body text — not titles
BODY_LINE_MIN = 60

# Max lines to merge into one paragraph before forcing a break
MAX_PARAGRAPH_LINES = 8

DEMO_TRANSCRIPT = """### [FAST] Transcript: [Tóm tắt sách Deep Work]
- Nguồn: https://www.youtube.com/watch?v=example
- Ngày: 13/05/2026
- Ngôn ngữ: vi

---

[00:00] Cứ 45 phút, bạn lại có một cuộc điện thoại.
[00:02] Thỉnh thoảng đồng nghiệp đến hỏi chuyện hay tán gẫu.
[00:05] Một giờ sau khi ăn trưa, bạn lại có một cuộc họp.
[00:08] Trước khi bạn kịp nhận ra rằng ngày hôm nay bạn vẫn chưa làm được gì
[00:11] thì đồng hồ đã chỉ 5h tan làng.
[00:14] Tại sao vậy?
[00:15] Đó là bởi vì bạn luôn bị môi trường bên ngoài quấy dày và gián đoạn.
[00:20] Bạn đang muốn giải quyết bài tập nhưng điện thoại cứ làm phiền.
[01:30] Vậy Deep Work là gì?
[01:31] Deep Work là tập trung hoàn toàn vào công việc trong trạng thái không bị can thiệp.
[01:36] Để khả năng của chúng ta đạt được giá trị cao nhất.
[01:39] Phương pháp làm việc này có thể giúp cho chúng ta tạo ra những giá trị mới.
[02:00] Vậy, Deep Work mang lại ý nghĩa gì cho chúng ta?
[02:33] Thì đầu tiên, Deep Work sẽ giúp chúng ta làm việc hiệu quả hơn.
[02:39] Theo tác giả, sẽ có 3 kiểu người sẽ ngày càng thành công hơn.
[02:44] Kiểu người đầu tiên đó chính là những người làm về kỹ thuật cao cấp.
[02:58] Kiểu người thứ 2 đó là Superstar.
[03:09] Kiểu người thứ 3 đó chính là các nhà tư bản.
[05:17] Thì điều đầu tiên, bạn cần phải tìm ra một mô hình tiếp quốc phù hợp với bản thân.
[05:22] Có 4 loại mô hình được xây dựng dựa trên 4 chiếc lý khác nhau.
[05:25] Chiếc lý đầu tiên đó là chiếc lý rũ bỏ mọi cám dỗ.
[05:43] Chiết lý thứ 2 là chiết lý đỉnh cao song song.
[05:52] Thứ 3 đó là chiết lý nhịp điệu.
[06:10] Chiết lý thứ 4 đó là chiết lý phóng viên.
"""


def strip_header(lines: list[str]) -> tuple[list[str], list[str]]:
    """Separate FAST transcript header from content lines.
    Returns (header_lines, content_lines) where content starts at the first timestamp.
    The header is returned for metadata purposes but should NOT be fed to content_mapper.
    """
    header = []
    content_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re.match(r"^\[\d+:\d+\]", stripped):
            content_start = i
            break
        header.append(line)
    return header, lines[content_start:]


def strip_timestamp(line: str) -> str:
    """Remove [MM:SS] or [HH:MM:SS] prefix from a line."""
    return re.sub(r"^\[\d+:\d+(?::\d+)?\]\s*", "", line).strip()


def is_pivot(text: str) -> bool:
    """Return True if this sentence signals a new topic/section."""
    text_lower = text.lower().strip()
    for pat in PIVOT_PATTERNS:
        if re.match(pat, text_lower, re.IGNORECASE):
            return True
    return False


def merge_lines_to_paragraphs(lines: list[str]) -> list[str]:
    """
    Merge fragmented ASR lines into coherent paragraphs.
    Insert blank lines before pivot sentences and after long paragraph runs.
    """
    paragraphs: list[str] = []
    current_paragraph: list[str] = []

    def flush(para: list[str]) -> None:
        if para:
            paragraphs.append(" ".join(para))
            paragraphs.append("")  # blank line after paragraph

    for raw_line in lines:
        if not raw_line.strip():
            # Preserve explicit blank lines
            flush(current_paragraph)
            current_paragraph = []
            continue

        # Lines that are metadata/separator (---, ###, -)
        if re.match(r"^(---+|#{1,3}\s|[-*]\s)", raw_line.strip()):
            flush(current_paragraph)
            current_paragraph = []
            paragraphs.append(raw_line.rstrip())
            paragraphs.append("")
            continue

        text = strip_timestamp(raw_line)
        if not text:
            continue

        if is_pivot(text):
            # Always start a new block before a pivot
            flush(current_paragraph)
            current_paragraph = []
            # Short pivot lines become standalone titles (blank line before + after)
            if len(text) <= 70:
                paragraphs.append(text)
                paragraphs.append("")
            else:
                # Long pivot line → start of a new paragraph
                current_paragraph.append(text)
            continue

        # Long paragraph protection: break after MAX_PARAGRAPH_LINES
        if len(current_paragraph) >= MAX_PARAGRAPH_LINES:
            flush(current_paragraph)
            current_paragraph = []

        current_paragraph.append(text)

    flush(current_paragraph)
    return paragraphs


def clean_output(paragraphs: list[str]) -> str:
    """Remove excessive blank lines and clean trailing whitespace."""
    lines = []
    prev_blank = False
    for line in paragraphs:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue  # collapse consecutive blanks
        lines.append(line)
        prev_blank = is_blank
    return "\n".join(lines).strip() + "\n"


def preprocess(text: str) -> str:
    """Return cleaned content only — no [FAST] metadata header.
    The header is stripped so content_mapper does not treat it as sections.
    """
    raw_lines = text.split("\n")
    _header_lines, content_lines = strip_header(raw_lines)
    processed_paragraphs = merge_lines_to_paragraphs(content_lines)
    return clean_output(processed_paragraphs)


def main():
    parser = argparse.ArgumentParser(
        description="Preprocess ASR transcripts before content mapping"
    )
    parser.add_argument("--input", help="Path to raw ASR transcript file")
    parser.add_argument("--output", help="Write cleaned transcript to file (default: stdout)")
    parser.add_argument("--demo", action="store_true", help="Run on built-in demo excerpt")
    args = parser.parse_args()

    if args.demo:
        print("Running DEMO MODE on built-in Deep Work ASR excerpt.\n")
        text = DEMO_TRANSCRIPT
    elif args.input:
        path = Path(args.input)
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text(encoding="utf-8")
    else:
        parser.print_help()
        sys.exit(1)

    cleaned = preprocess(text)

    if args.output:
        out = Path(args.output)
        out.write_text(cleaned, encoding="utf-8")
        print(f"  Cleaned transcript written to: {out}")
        # Stats
        raw_lines = [l for l in text.split("\n") if re.match(r"^\[\d+:\d+\]", l)]
        out_paragraphs = [l for l in cleaned.split("\n\n") if l.strip()]
        print(f"  Input: {len(raw_lines)} timestamp lines")
        print(f"  Output: {len(out_paragraphs)} paragraphs")
        print(f"\n  Next step: python scripts/content_mapper.py --input {out}\n")
    else:
        print("=" * 60)
        print("  PREPROCESSED TRANSCRIPT (pipe to content_mapper)")
        print("=" * 60)
        print()
        print(cleaned)
        print("=" * 60)
        raw_lines = [l for l in text.split("\n") if re.match(r"^\[\d+:\d+\]", l)]
        out_paragraphs = [l for l in cleaned.split("\n\n") if l.strip()]
        print(f"  Input: {len(raw_lines)} timestamp lines")
        print(f"  Output: {len(out_paragraphs)} paragraphs")
        print(f"\n  Next step: python scripts/content_mapper.py --input <output_file>")
        print(f"  Or pipe:   python scripts/preprocess_transcript.py --input x.txt --output clean.txt")
        print()


if __name__ == "__main__":
    main()
