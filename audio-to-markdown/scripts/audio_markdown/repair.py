"""Vietnamese mojibake detection and conservative repair."""

from __future__ import annotations

import re
from typing import Any

MOJIBAKE_RE = re.compile(
    "("
    r"\u00c3|"
    r"\u00c4|"
    r"\u00c2|"
    r"\u00c6|"
    r"\u00e1\u00ba|"
    r"\u00e1\u00bb|"
    r"\ufffd"
    ")"
)

VIETNAMESE_CHARS = set(
    "\u0103\u0102\u00e2\u00c2\u0111\u0110\u00ea\u00ca\u00f4\u00d4\u01a1\u01a0\u01b0\u01af"
    "\u00e1\u00e0\u1ea3\u00e3\u1ea1\u1ea5\u1ea7\u1ea9\u1eab\u1ead\u1eaf\u1eb1\u1eb3\u1eb5\u1eb7"
    "\u00c1\u00c0\u1ea2\u00c3\u1ea0\u1ea4\u1ea6\u1ea8\u1eaa\u1eac\u1eae\u1eb0\u1eb2\u1eb4\u1eb6"
    "\u00e9\u00e8\u1ebb\u1ebd\u1eb9\u1ebf\u1ec1\u1ec3\u1ec5\u1ec7"
    "\u00c9\u00c8\u1eba\u1ebc\u1eb8\u1ebe\u1ec0\u1ec2\u1ec4\u1ec6"
    "\u00ed\u00ec\u1ec9\u0129\u1ecb\u00cd\u00cc\u1ec8\u0128\u1eca"
    "\u00f3\u00f2\u1ecf\u00f5\u1ecd\u1ed1\u1ed3\u1ed5\u1ed7\u1ed9\u1edb\u1edd\u1edf\u1ee1\u1ee3"
    "\u00d3\u00d2\u1ece\u00d5\u1ecc\u1ed0\u1ed2\u1ed4\u1ed6\u1ed8\u1eda\u1edc\u1ede\u1ee0\u1ee2"
    "\u00fa\u00f9\u1ee7\u0169\u1ee5\u1ee9\u1eeb\u1eed\u1eef\u1ef1"
    "\u00da\u00d9\u1ee6\u0168\u1ee4\u1ee8\u1eea\u1eec\u1eee\u1ef0"
    "\u00fd\u1ef3\u1ef7\u1ef9\u1ef5\u00dd\u1ef2\u1ef6\u1ef8\u1ef4"
)


def mojibake_score(text: str) -> int:
    return len(MOJIBAKE_RE.findall(text))


def vietnamese_score(text: str) -> int:
    return sum(1 for char in text if char in VIETNAMESE_CHARS)


def repair_text_candidate(text: str) -> str:
    candidates = [text]
    for encoding in ("latin1", "cp1252"):
        try:
            candidates.append(text.encode(encoding, errors="ignore").decode("utf-8", errors="ignore"))
        except UnicodeError:
            pass
    try:
        raw = bytearray()
        for char in text:
            codepoint = ord(char)
            if codepoint <= 0xFF:
                raw.append(codepoint)
            else:
                raw.extend(char.encode("cp1252"))
        candidates.append(bytes(raw).decode("utf-8"))
    except UnicodeError:
        pass
    return max(candidates, key=lambda item: (vietnamese_score(item) - mojibake_score(item) * 2, len(item)))


def repair_vietnamese_segments(segments: list[dict[str, Any]]) -> dict[str, Any]:
    raw_text = "\n".join(str(segment.get("text", "")) for segment in segments)
    raw_mojibake = mojibake_score(raw_text)
    raw_vietnamese = vietnamese_score(raw_text)
    repaired: list[dict[str, Any]] = []
    changed = 0

    for segment in segments:
        copied = dict(segment)
        original = str(copied.get("text", ""))
        candidate = repair_text_candidate(original)
        if candidate and candidate != original:
            copied["raw_text"] = original
            copied["text"] = candidate
            changed += 1
        repaired.append(copied)

    repaired_text = "\n".join(str(segment.get("text", "")) for segment in repaired)
    repaired_mojibake = mojibake_score(repaired_text)
    repaired_vietnamese = vietnamese_score(repaired_text)
    confidence = "none"
    if raw_mojibake and repaired_mojibake < raw_mojibake and repaired_vietnamese >= raw_vietnamese:
        confidence = "high" if changed / max(len(segments), 1) >= 0.2 else "medium"

    applied = confidence in {"high", "medium"}
    return {
        "segments": repaired if applied else segments,
        "mojibake_detected": raw_mojibake > 0,
        "repair_applied": applied,
        "repair_confidence": confidence,
        "raw_mojibake_score": raw_mojibake,
        "repaired_mojibake_score": repaired_mojibake,
        "raw_vietnamese_score": raw_vietnamese,
        "repaired_vietnamese_score": repaired_vietnamese,
    }
