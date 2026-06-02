"""Transcript quality gates and hallucination/repetition checks."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from .models import QUALITY_FAILED, QUALITY_REVIEW, QUALITY_USABLE, QualityReport
from .text import clean_text, normalized_line


def shannon_entropy(tokens: list[str]) -> float:
    if not tokens:
        return 0.0
    counts = Counter(tokens)
    total = len(tokens)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def longest_repeat_run(lines: list[str]) -> int:
    longest = 0
    current = 0
    previous = None
    for line in lines:
        if line and line == previous:
            current += 1
        else:
            current = 1
            previous = line
        longest = max(longest, current)
    return longest


def assess_quality(segments: list[dict[str, Any]], duration_seconds: float | None = None) -> QualityReport:
    texts = [clean_text(str(segment.get("text", ""))) for segment in segments if str(segment.get("text", "")).strip()]
    joined = " ".join(texts)
    norm_lines = [normalized_line(text) for text in texts if normalized_line(text)]
    line_counts = Counter(norm_lines)
    tokens = re.findall(r"\w+", joined.lower(), flags=re.UNICODE)
    total_chars = sum(len(text) for text in texts)
    top_line, top_count = ("", 0)
    if line_counts:
        top_line, top_count = line_counts.most_common(1)[0]
    top_chars = len(top_line) * top_count
    metrics: dict[str, Any] = {
        "segment_count": len(texts),
        "unique_segment_ratio": round(len(line_counts) / max(len(norm_lines), 1), 3),
        "top_segment_ratio": round(top_count / max(len(norm_lines), 1), 3),
        "top_segment_char_ratio": round(top_chars / max(total_chars, 1), 3),
        "longest_repeat_run": longest_repeat_run(norm_lines),
        "token_entropy": round(shannon_entropy(tokens), 3),
        "unique_token_ratio": round(len(set(tokens)) / max(len(tokens), 1), 3),
        "duration_seconds": duration_seconds,
        "top_repeated_text": top_line[:160],
    }

    fail_reasons: list[str] = []
    if metrics["top_segment_char_ratio"] >= 0.5 and len(texts) >= 2:
        fail_reasons.append("One repeated sentence accounts for at least half of transcript characters.")
    if len(texts) >= 20 and metrics["unique_segment_ratio"] <= 0.15:
        fail_reasons.append("Transcript has very few unique segments for its length.")
    if len(texts) >= 10 and metrics["longest_repeat_run"] >= 8 and len(top_line) >= 20:
        fail_reasons.append("Transcript contains a long consecutive repeat run.")
    if len(tokens) >= 100 and metrics["token_entropy"] < 3.0:
        fail_reasons.append("Token entropy is unusually low.")
    if duration_seconds and duration_seconds > 600 and len(tokens) < 80:
        fail_reasons.append("Transcript is too short for a long recording.")

    review_reasons: list[str] = []
    if len(texts) >= 10 and metrics["top_segment_ratio"] >= 0.25:
        review_reasons.append("Repeated segment pattern detected.")
    if len(texts) >= 10 and metrics["longest_repeat_run"] >= 8:
        review_reasons.append("Short repeated acknowledgement pattern detected.")
    if len(tokens) >= 100 and metrics["unique_token_ratio"] < 0.12:
        review_reasons.append("Vocabulary diversity is low.")

    if fail_reasons:
        return QualityReport(QUALITY_FAILED, True, fail_reasons, metrics)
    if review_reasons:
        return QualityReport(QUALITY_REVIEW, False, review_reasons, metrics)
    return QualityReport(QUALITY_USABLE, False, [], metrics)

