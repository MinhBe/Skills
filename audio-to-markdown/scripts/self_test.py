#!/usr/bin/env python3
"""Offline checks for audio-to-markdown behavior."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = SKILL_ROOT.parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "audio_to_markdown.py"
FIXTURES = REPO_ROOT / "Asset" / "Record_Transcript"


VOICE_008_INLINE = """# Transcript

| Time | Speaker | Text |
|---|---|---|
""" + "\n".join(
    f"| 00:{idx:02d}:00 | Speaker 1 | H\u00c3\u00a3y subscribe cho k\u00c3\u00aanh Ghi\u00e1\u00bb\u0081n M\u00c3\u00ac G\u00c3\u00b5 \u00c4\u0090\u00e1\u00bb\u0083 kh\u00c3\u00b4ng b\u00e1\u00bb\u008f l\u00e1\u00bb\u00a1 nh\u00e1\u00bb\u00afng video h\u00e1\u00ba\u00a5p d\u00e1\u00ba\u00abn. |"
    for idx in range(24)
) + "\n"

RESEARCH_INLINE = """# Transcript

| Time | Speaker | Text |
|---|---|---|
| 00:00:05 | Speaker 1 | Em phải bổ sung nguồn dữ liệu và giải thích rõ từng trường. |
| 00:00:20 | Speaker 1 | Tên bộ dữ liệu là gì? |
| 00:00:35 | Speaker 1 | Vấn đề của em là phần đánh nhãn còn chủ quan và không rõ. |
| 00:00:50 | Speaker 1 | Lần sau em chuẩn bị bảng so sánh và nêu hết các nguồn. |
"""

SECOND_RESEARCH_INLINE = """# Transcript

| Time | Speaker | Text |
|---|---|---|
| 00:00:05 | Speaker 1 | Đây đây, em đang làm nó đang hơi không kiểm soát được. |
| 00:00:15 | Speaker 1 | Em cần làm rõ mục tiêu và bổ sung phần đánh giá. |
| 00:00:30 | Speaker 1 | Vậy dữ liệu lấy ở đâu và tỷ lệ mất cân bằng như thế nào? |
"""


def run_cli(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False)


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def fixture_path(temp_dir: Path, filename: str, fallback_text: str) -> Path:
    local = temp_dir / filename
    local.write_text(fallback_text, encoding="utf-8")
    return local


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="atm_selftest_") as temp:
        temp_dir = Path(temp)

        fail_out = temp_dir / "voice_008.md"
        voice_fixture = fixture_path(temp_dir, "Voice 008_sd.md", VOICE_008_INLINE)
        proc = run_cli(
            [
                "--input",
                "missing-audio.m4a",
                "--transcript",
                str(voice_fixture),
                "--output",
                str(fail_out),
                "--language",
                "vi",
            ]
        )
        assert_true(proc.returncode == 2, "Voice 008 fixture should fail quality gate.")
        fail_text = fail_out.read_text(encoding="utf-8")
        assert_true("failed_stt_quality_gate" in fail_text, "Failure report should include failed status.")
        assert_true("## Action Items" not in fail_text, "Failure report must not render full action items.")

        meeting_out = temp_dir / "thay_lam.md"
        meeting_fixture = fixture_path(temp_dir, "Thầy lâm 2.md", RESEARCH_INLINE)
        proc = run_cli(
            [
                "--input",
                "missing-audio.m4a",
                "--transcript",
                str(meeting_fixture),
                "--output",
                str(meeting_out),
                "--profile",
                "research_meeting",
                "--language",
                "vi",
                "--emit-analysis",
            ]
        )
        assert_true(proc.returncode == 0, f"Research fixture should render successfully: {proc.stderr}")
        meeting_text = meeting_out.read_text(encoding="utf-8")
        analysis_text = meeting_out.with_name("thay_lam_analysis.md").read_text(encoding="utf-8")
        for heading in ["Advisor Questions", "Required Revisions", "Weak Points Raised", "Next Meeting Checklist"]:
            assert_true(heading in meeting_text, f"Missing research section: {heading}")
        assert_true("| Student |" in meeting_text or "| Unclear |" in meeting_text, "Action table should have owner evidence.")
        assert_true("Evidence-Based Action Items" in analysis_text, "Analysis file should be emitted.")

        second_out = temp_dir / "record_thay_lam_2.md"
        second_fixture = fixture_path(temp_dir, "Record thầy Lâm (2).md", SECOND_RESEARCH_INLINE)
        proc = run_cli(
            [
                "--input",
                "missing-audio.m4a",
                "--transcript",
                str(second_fixture),
                "--output",
                str(second_out),
                "--profile",
                "research_meeting",
                "--language",
                "vi",
            ]
        )
        assert_true(proc.returncode == 0, f"Second research fixture should render successfully: {proc.stderr}")
        second_text = second_out.read_text(encoding="utf-8")
        assert_true("Weak Points Raised" in second_text, "Second fixture should include research weakness section.")
        assert_true("không kiểm soát" in second_text, "Second fixture should preserve readable Vietnamese text.")

        sys.path.insert(0, str(SKILL_ROOT / "scripts"))
        from audio_markdown.quality import assess_quality
        from audio_markdown.repair import repair_vietnamese_segments
        from audio_markdown.render import extract_action_items

        mojibake = [{"start": 0, "text": "H\u00c3\u00a3y subscribe cho k\u00c3\u00aAnh."}]
        repaired = repair_vietnamese_segments(mojibake)
        assert_true(repaired["repair_applied"], "Mojibake repair should apply.")
        assert_true("Hãy" in repaired["segments"][0]["text"], "Mojibake sample should become readable Vietnamese.")

        valid_vietnamese = [{"start": 0, "text": "Âm lượng ổn và nội dung đã rõ."}]
        valid_repair = repair_vietnamese_segments(valid_vietnamese)
        assert_true(not valid_repair["repair_applied"], "Valid Vietnamese should not be rewritten as mojibake.")

        normal = [{"start": 0, "text": "Em phải bổ sung bảng kết quả và giải thích rõ dữ liệu."}]
        assert_true(assess_quality(normal).status != "failed_stt_quality_gate", "Short normal transcript should not fail.")
        actions = extract_action_items(normal)
        assert_true(actions and actions[0]["owner"] == "Student", "Action extraction should infer Student owner.")

        json.load((SKILL_ROOT / "evals" / "evals.json").open(encoding="utf-8"))

    print("audio-to-markdown self-test ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
