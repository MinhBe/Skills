"""Markdown rendering and research-meeting extraction."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from .models import QUALITY_FAILED, QUALITY_REVIEW
from .text import clean_text, fmt_duration, fmt_time, markdown_escape, normalized_line

ACTION_RE = re.compile(
    "("
    r"\bem\s+ph\u1ea3i\b|"
    r"\bph\u1ea3i\b|"
    r"\bc\u1ea7n\b|"
    r"\bl\u1ea7n sau\b|"
    r"\bchu\u1ea9n b\u1ecb\b|"
    r"\bgi\u1ea3i th\u00edch\b|"
    r"\bn\u00eau\b|"
    r"\bs\u1eeda\b|"
    r"\bb\u1ed5 sung\b|"
    r"\bl\u00e0m r\u00f5\b"
    ")",
    re.I,
)

HIGH_CONFIDENCE_ACTION_RE = re.compile(
    r"\b(em\s+ph\u1ea3i|ph\u1ea3i|c\u1ea7n|chu\u1ea9n b\u1ecb)\b",
    re.I,
)

QUESTION_RE = re.compile(
    "("
    r"\?|"
    r"\b\u0111\u00fang kh\u00f4ng\b|"
    r"\bl\u00e0 g\u00ec\b|"
    r"\bnh\u01b0 th\u1ebf n\u00e0o\b|"
    r"\b\u1edf \u0111\u00e2u\b|"
    r"\bv\u00ec sao\b|"
    r"\bt\u1ea1i sao\b|"
    r"\bch\u01b0a\b"
    ")",
    re.I,
)

WEAKNESS_RE = re.compile(
    "("
    r"v\u1ea5n \u0111\u1ec1|"
    r"y\u1ebfu|"
    r"thi\u1ebfu|"
    r"kh\u00f4ng r\u00f5|"
    r"kh\u00f4ng ki\u1ec3m so\u00e1t|"
    r"m\u1ea5t c\u00e2n b\u1eb1ng|"
    r"ch\u1ee7 quan"
    ")",
    re.I,
)


def runtime_verdict(advisor: dict[str, Any]) -> str:
    if advisor.get("ok"):
        return advisor["report"].get("verdict", {}).get("classification", "unknown")
    return "unknown"


def render_attempts(stt: dict[str, Any]) -> list[str]:
    attempts = stt.get("attempts", [])
    if not attempts:
        return ["- No fallback attempt log available."]
    rows = ["| Engine | Model | Status | Error |", "|---|---|---|---|"]
    for attempt in attempts:
        rows.append(
            f"| {attempt.get('engine', '')} | {attempt.get('model', '')} | {'ok' if attempt.get('ok') else 'failed'} | {markdown_escape(str(attempt.get('error', '')))} |"
        )
    return rows


def extract_key_points(segments: list[dict[str, Any]], limit: int = 8) -> list[str]:
    points = []
    seen: set[str] = set()
    for segment in segments:
        text = clean_text(str(segment.get("text", "")))
        norm = normalized_line(text)
        if len(text) >= 40 and norm not in seen:
            seen.add(norm)
            points.append(text)
        if len(points) >= limit:
            break
    return points


def extract_action_items(segments: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    items = []
    seen: set[str] = set()
    for segment in segments:
        text = clean_text(str(segment.get("text", "")))
        if not ACTION_RE.search(text):
            continue
        norm = normalized_line(text)
        if norm in seen:
            continue
        seen.add(norm)
        lower = text.lower()
        owner = "Student" if "em " in lower or lower.startswith("em") else "Unclear"
        confidence = "high" if HIGH_CONFIDENCE_ACTION_RE.search(lower) else "medium"
        items.append(
            {
                "owner": owner,
                "task": text,
                "timestamp": fmt_time(float(segment.get("start", 0.0))),
                "evidence": text,
                "confidence": confidence,
            }
        )
        if len(items) >= limit:
            break
    return items


def select_matching(segments: list[dict[str, Any]], pattern: re.Pattern[str], limit: int = 8) -> list[str]:
    items = []
    seen = set()
    for segment in segments:
        text = clean_text(str(segment.get("text", "")))
        norm = normalized_line(text)
        if pattern.search(text) and norm not in seen:
            seen.add(norm)
            stamp = fmt_time(float(segment.get("start", 0.0)))
            items.append(f"{stamp + ' - ' if stamp else ''}{text}")
        if len(items) >= limit:
            break
    return items


def render_action_items(items: list[dict[str, Any]]) -> list[str]:
    rows = ["| Owner | Task | Timestamp | Evidence | Confidence |", "|---|---|---|---|---|"]
    if not items:
        rows.append("| Unclear | No explicit action item detected by the script. | Not specified | No evidence found. | low |")
        return rows
    for item in items:
        rows.append(
            f"| {item['owner']} | {markdown_escape(item['task'])} | {item['timestamp'] or 'Not specified'} | {markdown_escape(item['evidence'])} | {item['confidence']} |"
        )
    return rows


def render_research_meeting_sections(segments: list[dict[str, Any]], action_items: list[dict[str, Any]]) -> list[str]:
    question_items = select_matching(segments, QUESTION_RE)
    requirement_items = [item["evidence"] for item in action_items[:8]]
    weakness_items = select_matching(segments, WEAKNESS_RE)
    md = ["", "## Research Meeting Analysis", ""]
    md.extend(["### Advisor Questions", ""])
    md.extend([f"- {item}" for item in question_items] or ["- Not explicitly identified."])
    md.extend(["", "### Required Revisions", ""])
    md.extend([f"- {item}" for item in requirement_items] or ["- Not explicitly identified."])
    md.extend(["", "### Weak Points Raised", ""])
    md.extend([f"- {item}" for item in weakness_items] or ["- Not explicitly identified."])
    md.extend(["", "### Unanswered Questions", ""])
    md.extend([f"- {item}" for item in question_items[:5]] or ["- Not explicitly identified."])
    md.extend(["", "### Next Actions", ""])
    md.extend([f"- {item['task']}" for item in action_items[:8]] or ["- Not explicitly identified."])
    md.extend(["", "### Next Meeting Checklist", ""])
    checklist = [item["task"] for item in action_items[:8]]
    md.extend([f"- [ ] {item}" for item in checklist] or ["- [ ] Review transcript and identify preparation items manually."])
    return md


def render_failed_quality_report(source: Path, profile: str, advisor: dict[str, Any], normalization: dict[str, Any], stt: dict[str, Any], quality: dict[str, Any], audio_info: dict[str, Any], language: str | None) -> str:
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    sample = [clean_text(segment.get("text", "")) for segment in stt.get("segments", [])[:8]]
    md = [
        "# Audio Markdown Quality Failure",
        "",
        "## Metadata",
        "",
        f"- Source file: `{source}`",
        f"- Created: {now}",
        f"- Profile: {profile}",
        f"- Language: {stt.get('language') or language or 'auto/unknown'}",
        f"- Duration: {fmt_duration(audio_info.get('duration_seconds'))}",
        f"- Quality status: `{QUALITY_FAILED}`",
        "",
        "## Pipeline",
        "",
        f"- Runtime verdict: `{runtime_verdict(advisor)}`",
        f"- Normalization: {'completed' if normalization.get('ok') else 'skipped/failed'}",
        f"- STT engine: {stt.get('engine', 'none')}",
        f"- Model: {stt.get('model', 'unknown')}",
        "",
        "## Failure Reasons",
        "",
    ]
    md.extend([f"- {reason}" for reason in quality.get("reasons", [])] or ["- Transcript failed quality gate."])
    md.extend(["", "## Quality Metrics", "", "```json", json.dumps(quality.get("metrics", {}), ensure_ascii=False, indent=2), "```"])
    md.extend(["", "## Raw Transcript Sample", ""])
    md.extend([f"- {item}" for item in sample] or ["- No transcript sample available."])
    md.extend(["", "## Recommended Rerun", "", "- Retranscribe with chunking enabled, for example `--chunk-minutes 5`.", "- Review audio warnings before trusting a new transcript.", "- Try a different cached local model if available; fallback attempts are listed below.", "", "## Fallback Attempts", ""])
    md.extend(render_attempts(stt))
    md.extend(["", "## Audio Warnings", ""])
    md.extend([f"- {warning}" for warning in audio_info.get("warnings", [])] or ["- No audio precheck warnings."])
    return "\n".join(md) + "\n"


def render_markdown(source: Path, profile: str, advisor: dict[str, Any], normalization: dict[str, Any], stt: dict[str, Any], quality: dict[str, Any], repair: dict[str, Any], audio_info: dict[str, Any], language: str | None) -> str:
    if quality["status"] == QUALITY_FAILED:
        return render_failed_quality_report(source, profile, advisor, normalization, stt, quality, audio_info, language)

    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    participants = sorted({segment.get("speaker", "Speaker 1") for segment in stt.get("segments", [])}) or ["Unknown"]
    key_points = extract_key_points(stt.get("segments", []))
    action_items = extract_action_items(stt.get("segments", []))
    transcript_rows = [
        f"| {fmt_time(float(segment.get('start', 0.0)))} | {segment.get('speaker', 'Speaker 1')} | {markdown_escape(segment.get('text', ''))} |"
        for segment in stt.get("segments", [])
    ]

    quality_notes = []
    if quality["status"] == QUALITY_REVIEW:
        quality_notes.append("Quality status is `needs_review`; review repeated or low-diversity transcript spans before relying on analysis.")
    if not advisor.get("ok"):
        quality_notes.append(f"Runtime advisor did not run: {advisor.get('error', 'unknown error')}")
    if audio_info.get("warnings"):
        quality_notes.extend(audio_info["warnings"])
    if not normalization.get("ok"):
        quality_notes.append(f"Audio normalization skipped or failed: {normalization.get('reason') or 'see ffmpeg output'}")
    if not stt.get("ok"):
        quality_notes.append(stt.get("error", "STT failed"))
    if repair.get("mojibake_detected"):
        applied = "applied" if repair.get("repair_applied") else "not applied"
        quality_notes.append(f"Vietnamese mojibake detected; repair {applied} with confidence `{repair.get('repair_confidence')}`.")
    if stt.get("engine") != "provided-transcript":
        quality_notes.append("Transcript is machine-generated and should be reviewed for names, numbers, acronyms, and unclear speech.")
    if len(participants) == 1:
        quality_notes.append("Speaker diarization was not available; speaker labels may be incomplete.")

    title_map = {"meeting": "Meeting Notes", "research": "Research Notes", "research_meeting": "Research Meeting Notes", "interview": "Interview Notes", "lecture": "Lecture Notes"}
    summary_map = {"meeting": "Meeting Summary", "research": "Research Summary", "research_meeting": "Research Meeting Summary", "interview": "Interview Summary", "lecture": "Lecture Summary"}
    title = title_map.get(profile, "Audio Markdown")
    summary_heading = summary_map.get(profile, "Summary")

    md = [
        f"# {title}",
        "",
        "## Metadata",
        "",
        f"- Source file: `{source}`",
        f"- Created: {now}",
        f"- Profile: {profile}",
        f"- Language: {stt.get('language') or language or 'auto/unknown'}",
        f"- Duration: {fmt_duration(audio_info.get('duration_seconds'))}",
        f"- Quality status: `{quality['status']}`",
        "",
        "## Pipeline",
        "",
        f"- Runtime verdict: `{runtime_verdict(advisor)}`",
        f"- Normalization: {'completed' if normalization.get('ok') else 'skipped/failed'}",
        f"- STT engine: {stt.get('engine', 'none')}",
        f"- Model: {stt.get('model', 'unknown')}",
        "- Speaker diarization: not available in default local path",
        "",
        "## Participants",
        "",
    ]
    md.extend([f"- {participant}" for participant in participants])
    md.extend(["", "## Transcript", "", "| Time | Speaker | Text |", "|---|---|---|"])
    md.extend(transcript_rows or ["|  |  | Transcript unavailable. |"])
    md.extend(["", f"## {summary_heading}", "", "- " + (" ".join(key_points[:2]) if key_points else "Summary unavailable until transcription succeeds.")])
    if profile in {"meeting", "research_meeting"}:
        md.extend(["", "## Decisions", "", "- Not explicitly identified."])
    md.extend(["", "## Key Points", ""])
    md.extend([f"- {point}" for point in key_points] or ["- Not available."])
    if profile == "research_meeting":
        md.extend(render_research_meeting_sections(stt.get("segments", []), action_items))
    md.extend(["", "## Recommendations", "", "- Review transcript quality notes before using this as an authoritative record.", "", "## Action Items", ""])
    md.extend(render_action_items(action_items))
    md.extend(["", "## Risks And Open Questions", "", "- Confirm names, dates, numbers, and technical terms against the source audio.", "", "## Quality Metrics", "", "```json", json.dumps(quality.get("metrics", {}), ensure_ascii=False, indent=2), "```", "", "## Fallback Attempts", ""])
    md.extend(render_attempts(stt))
    md.extend(["", "## Quality Notes", ""])
    md.extend([f"- {note}" for note in quality_notes] or ["- No quality issues detected by the script."])
    return "\n".join(md) + "\n"


def render_analysis_file(source: Path, stt: dict[str, Any], quality: dict[str, Any]) -> str:
    action_items = extract_action_items(stt.get("segments", []))
    now = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    md = ["# Research Meeting Analysis", "", f"- Source file: `{source}`", f"- Created: {now}", f"- Quality status: `{quality['status']}`"]
    md.extend(render_research_meeting_sections(stt.get("segments", []), action_items))
    md.extend(["", "## Evidence-Based Action Items", ""])
    md.extend(render_action_items(action_items))
    return "\n".join(md) + "\n"

