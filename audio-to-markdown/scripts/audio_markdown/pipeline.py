"""Top-level pipeline orchestration."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from .models import QUALITY_FAILED, QUALITY_USABLE
from .quality import assess_quality
from .repair import repair_vietnamese_segments
from .render import render_analysis_file, render_markdown
from .stt import choose_stt, inspect_audio, normalize, probe_duration, run_advisor


def print_output_path(output: Path) -> None:
    text = str(output)
    try:
        print(text)
    except UnicodeEncodeError:
        encoded = text.encode(sys.stdout.encoding or "utf-8", errors="backslashreplace")
        sys.stdout.buffer.write(encoded + b"\n")
        sys.stdout.flush()


def run_pipeline(
    *,
    source: Path,
    output: Path,
    profile: str,
    language: str | None,
    model: str,
    fallback_models: str | None,
    transcript: Path | None,
    audio_minutes: float | None,
    chunk_minutes: float,
    keep_normalized: bool,
    analysis_output: Path | None,
    emit_analysis: bool,
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)

    advisor = run_advisor(audio_minutes)
    audio_info = inspect_audio(source)
    temp_dir_obj = tempfile.TemporaryDirectory()
    temp_dir = Path(temp_dir_obj.name)
    normalized_path, normalization = normalize(source, temp_dir) if not transcript else (source, {"ok": False, "skipped": True, "reason": "provided transcript"})

    try:
        try:
            stt = choose_stt(normalized_path, model, language, transcript, fallback_models, chunk_minutes)
        except Exception as exc:  # noqa: BLE001
            stt = {"ok": False, "engine": "local-stt", "model": model, "segments": [], "error": str(exc), "attempts": []}

        repair = repair_vietnamese_segments(stt.get("segments", []))
        stt["segments"] = repair["segments"]

        duration = audio_info.get("duration_seconds") or probe_duration(normalized_path)
        quality_report = assess_quality(stt.get("segments", []), duration)
        if repair.get("repair_applied") and quality_report.status == QUALITY_USABLE:
            quality_report.status = QUALITY_REVIEW
            quality_report.reasons.append("Vietnamese mojibake was detected and repaired.")
        if not stt.get("ok") and quality_report.status != QUALITY_FAILED:
            quality_report.status = QUALITY_FAILED
            quality_report.suspected_stt_hallucination = False
            quality_report.reasons.append(stt.get("error", "STT failed."))

        quality = quality_report.to_dict()
        md = render_markdown(source, profile, advisor, normalization, stt, quality, repair, audio_info, language)
        output.write_text(md, encoding="utf-8")

        should_emit_analysis = emit_analysis or bool(analysis_output)
        if profile == "research_meeting" and should_emit_analysis and quality["status"] != QUALITY_FAILED:
            analysis_path = analysis_output if analysis_output else output.with_name(f"{output.stem}_analysis.md")
            analysis_path.parent.mkdir(parents=True, exist_ok=True)
            analysis_path.write_text(render_analysis_file(source, stt, quality), encoding="utf-8")

        if keep_normalized and normalization.get("ok"):
            kept = output.with_suffix(".normalized.wav")
            shutil.copyfile(normalized_path, kept)
    finally:
        temp_dir_obj.cleanup()

    print_output_path(output)
    return 0 if stt.get("ok") and quality["status"] != QUALITY_FAILED else 2
