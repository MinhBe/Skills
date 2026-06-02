"""Small text utilities shared across the pipeline."""

from __future__ import annotations

import re


def parse_time(value: str) -> float:
    if not value:
        return 0.0
    parts = value.split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return float(value)
    except ValueError:
        return 0.0


def fmt_time(seconds: float | None) -> str:
    if not seconds:
        return ""
    seconds_i = int(seconds)
    h, rem = divmod(seconds_i, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "not measured"
    return fmt_time(seconds) or "00:00:00"


def clean_text(text: str) -> str:
    text = " ".join(str(text).split())
    if text and text[-1] not in ".!?)]":
        text += "."
    return text


def markdown_escape(text: str) -> str:
    return clean_text(text).replace("|", "\\|")


def normalized_line(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower(), flags=re.UNICODE).strip()

