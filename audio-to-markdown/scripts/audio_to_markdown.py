#!/usr/bin/env python3
"""CLI wrapper for the local-first audio-to-Markdown pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from audio_markdown.pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert audio or an existing transcript to structured Markdown.")
    parser.add_argument("--input", "-i", required=True)
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument(
        "--profile",
        default="general",
        choices=["general", "meeting", "interview", "lecture", "research", "research_meeting"],
    )
    parser.add_argument("--language", default=None)
    parser.add_argument("--model", default="medium")
    parser.add_argument("--fallback-models", default=None, help="Comma-separated extra local model names to try before built-in fallback.")
    parser.add_argument("--transcript", default=None, help="Existing transcript text/Markdown file to format instead of running STT.")
    parser.add_argument("--audio-minutes", type=float, default=None)
    parser.add_argument("--chunk-minutes", type=float, default=7.5)
    parser.add_argument("--keep-normalized", action="store_true")
    parser.add_argument("--analysis-output", default=None, help="Optional separate research meeting analysis Markdown path.")
    parser.add_argument("--emit-analysis", action="store_true", help="Write a separate *_analysis.md file for research_meeting profile.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return run_pipeline(
        source=Path(args.input),
        output=Path(args.output),
        profile=args.profile,
        language=args.language,
        model=args.model,
        fallback_models=args.fallback_models,
        transcript=Path(args.transcript) if args.transcript else None,
        audio_minutes=args.audio_minutes,
        chunk_minutes=args.chunk_minutes,
        keep_normalized=args.keep_normalized,
        analysis_output=Path(args.analysis_output) if args.analysis_output else None,
        emit_analysis=args.emit_analysis,
    )


if __name__ == "__main__":
    raise SystemExit(main())
