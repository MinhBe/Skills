"""Shared data structures for the audio-to-markdown pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


QualityStatus = Literal["usable", "needs_review", "failed_stt_quality_gate"]

QUALITY_USABLE: QualityStatus = "usable"
QUALITY_REVIEW: QualityStatus = "needs_review"
QUALITY_FAILED: QualityStatus = "failed_stt_quality_gate"


@dataclass
class Segment:
    start: float = 0.0
    end: float = 0.0
    speaker: str = "Speaker 1"
    text: str = ""
    raw_text: str | None = None
    order: int | None = None

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "Segment":
        return cls(
            start=float(data.get("start") or 0.0),
            end=float(data.get("end") or 0.0),
            speaker=str(data.get("speaker") or "Speaker 1"),
            text=str(data.get("text") or ""),
            raw_text=str(data["raw_text"]) if data.get("raw_text") is not None else None,
            order=int(data["order"]) if data.get("order") is not None else None,
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "start": self.start,
            "end": self.end,
            "speaker": self.speaker,
            "text": self.text,
        }
        if self.raw_text is not None:
            data["raw_text"] = self.raw_text
        if self.order is not None:
            data["order"] = self.order
        return data


@dataclass
class QualityReport:
    status: QualityStatus
    suspected_stt_hallucination: bool
    reasons: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "suspected_stt_hallucination": self.suspected_stt_hallucination,
            "reasons": self.reasons,
            "metrics": self.metrics,
        }


@dataclass
class ActionItem:
    owner: str
    task: str
    timestamp: str
    evidence: str
    confidence: str

    def to_dict(self) -> dict[str, str]:
        return {
            "owner": self.owner,
            "task": self.task,
            "timestamp": self.timestamp,
            "evidence": self.evidence,
            "confidence": self.confidence,
        }


@dataclass
class PipelineReport:
    source: str
    profile: str
    language: str | None
    advisor: dict[str, Any]
    normalization: dict[str, Any]
    stt: dict[str, Any]
    repair: dict[str, Any]
    audio_info: dict[str, Any]
    quality: QualityReport

