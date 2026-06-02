#!/usr/bin/env python3
"""Normalize audio for speech-to-text with ffmpeg."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def normalize_audio(input_path: str, output_path: str, sample_rate: int = 16000) -> dict:
    if not shutil.which("ffmpeg"):
        return {"ok": False, "error": "ffmpeg not found"}

    inp = Path(input_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(inp),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-af",
        "loudnorm",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return {
        "ok": proc.returncode == 0,
        "input": str(inp),
        "output": str(out),
        "returncode": proc.returncode,
        "stderr_tail": proc.stderr[-2000:],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize audio for STT.")
    parser.add_argument("--input", "-i", required=True)
    parser.add_argument("--output", "-o", required=True)
    parser.add_argument("--sample-rate", type=int, default=16000)
    args = parser.parse_args()
    result = normalize_audio(args.input, args.output, args.sample_rate)
    if not result["ok"]:
        print(result.get("error") or result.get("stderr_tail") or "normalization failed")
        return 1
    print(result["output"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
