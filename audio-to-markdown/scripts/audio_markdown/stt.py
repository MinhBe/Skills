"""Local-first STT helpers, transcript parsing, and chunk fallback."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .models import QUALITY_FAILED
from .quality import assess_quality
from .text import parse_time


def script_root() -> Path:
    return Path(__file__).resolve().parents[1]


def advisor_script() -> Path:
    return script_root().parents[1] / "model-runtime-advisor" / "scripts" / "inspect_runtime.py"


def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def run_advisor(audio_minutes: float | None = None) -> dict[str, Any]:
    script = advisor_script()
    if not script.exists():
        return {"ok": False, "error": "model-runtime-advisor script not found"}
    cmd = [sys.executable, str(script), "--workload", "stt"]
    if audio_minutes is not None:
        cmd.extend(["--audio-minutes", str(audio_minutes)])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as handle:
        json_path = handle.name
    cmd.extend(["--output-json", json_path])
    try:
        proc = run_cmd(cmd)
        if proc.returncode != 0:
            return {"ok": False, "error": proc.stderr or proc.stdout}
        return {"ok": True, "report": json.loads(Path(json_path).read_text(encoding="utf-8"))}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    finally:
        Path(json_path).unlink(missing_ok=True)


def normalize(input_path: Path, output_dir: Path) -> tuple[Path, dict[str, Any]]:
    if not shutil.which("ffmpeg"):
        return input_path, {"ok": False, "skipped": True, "reason": "ffmpeg not found"}
    out = output_dir / f"{input_path.stem}.normalized.wav"
    cmd = [
        sys.executable,
        "-X",
        "utf8",
        str(script_root() / "normalize_audio.py"),
        "--input",
        str(input_path),
        "--output",
        str(out),
    ]
    proc = run_cmd(cmd)
    if proc.returncode == 0 and out.exists():
        return out, {"ok": True, "output": str(out)}
    return input_path, {"ok": False, "stderr_tail": proc.stderr[-2000:], "stdout": proc.stdout}


def probe_duration(path: Path) -> float | None:
    if not shutil.which("ffprobe"):
        return None
    proc = run_cmd(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    try:
        return float(proc.stdout.strip()) if proc.returncode == 0 else None
    except ValueError:
        return None


def inspect_audio(path: Path) -> dict[str, Any]:
    info: dict[str, Any] = {"duration_seconds": probe_duration(path), "warnings": []}
    if not shutil.which("ffmpeg"):
        info["warnings"].append("ffmpeg not found; audio volume/silence checks were skipped.")
        return info
    if not path.exists():
        info["warnings"].append("Input audio path does not exist or was not provided locally.")
        return info

    vol = run_cmd(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"])
    mean_match = __import__("re").search(r"mean_volume:\s*([-0-9.]+)\s*dB", vol.stderr)
    max_match = __import__("re").search(r"max_volume:\s*([-0-9.]+)\s*dB", vol.stderr)
    if mean_match:
        info["mean_volume_db"] = float(mean_match.group(1))
        if info["mean_volume_db"] < -35:
            info["warnings"].append("Mean volume is very low; STT accuracy may be poor.")
    if max_match:
        info["max_volume_db"] = float(max_match.group(1))
        if info["max_volume_db"] > -0.5:
            info["warnings"].append("Audio may be clipped or too hot near 0 dB.")
    return info


def transcribe_faster_whisper(audio_path: Path, model: str, language: str | None) -> dict[str, Any]:
    from faster_whisper import WhisperModel  # type: ignore

    whisper_model = WhisperModel(model, device="auto", compute_type="auto", local_files_only=True)
    segments, info = whisper_model.transcribe(str(audio_path), language=language)
    rows = [
        {"start": float(segment.start), "end": float(segment.end), "speaker": "Speaker 1", "text": segment.text.strip()}
        for segment in segments
    ]
    return {"ok": True, "engine": "faster-whisper", "model": model, "language": getattr(info, "language", language), "segments": rows}


def transcribe_openai_whisper(audio_path: Path, model: str, language: str | None) -> dict[str, Any]:
    import whisper  # type: ignore

    whisper_model = whisper.load_model(model)
    result = whisper_model.transcribe(str(audio_path), language=language)
    rows = [
        {
            "start": float(segment.get("start", 0)),
            "end": float(segment.get("end", 0)),
            "speaker": "Speaker 1",
            "text": str(segment.get("text", "")).strip(),
        }
        for segment in result.get("segments", [])
    ]
    if not rows and result.get("text"):
        rows.append({"start": 0.0, "end": 0.0, "speaker": "Speaker 1", "text": result["text"].strip()})
    return {"ok": True, "engine": "openai-whisper", "model": model, "language": result.get("language", language), "segments": rows}


def parse_markdown_transcript(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("| Time | Speaker | Text |"):
            in_table = True
            continue
        if in_table and (not stripped.startswith("|") or stripped.startswith("## ")):
            break
        if not in_table or stripped.startswith("|---"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 3:
            continue
        rows.append({"start": parse_time(cells[0]), "end": 0.0, "speaker": cells[1] or "Speaker 1", "text": cells[2]})
    return rows


def read_transcript(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    rows = parse_markdown_transcript(text)
    if not rows:
        for idx, line in enumerate([line.strip() for line in text.splitlines() if line.strip()]):
            rows.append({"start": 0.0, "end": 0.0, "speaker": "Speaker 1", "text": line, "order": idx})
    return {"ok": True, "engine": "provided-transcript", "model": "none", "language": None, "segments": rows}


def fallback_plan(model: str, raw_fallbacks: str | None) -> list[tuple[str, str]]:
    requested = [item.strip() for item in (raw_fallbacks or "").split(",") if item.strip()]
    faster_models = [model] + requested + ["medium", "small", "large-v3"]
    plan: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in faster_models:
        candidate = ("faster-whisper", item)
        if candidate not in seen:
            seen.add(candidate)
            plan.append(candidate)
    for item in ["medium", "small", "base"]:
        candidate = ("openai-whisper", item)
        if candidate not in seen:
            seen.add(candidate)
            plan.append(candidate)
    return plan


def transcribe_with_fallback(audio_path: Path, model: str, language: str | None, raw_fallbacks: str | None) -> dict[str, Any]:
    attempts = []
    for engine, candidate_model in fallback_plan(model, raw_fallbacks):
        if engine == "faster-whisper" and importlib.util.find_spec("faster_whisper") is None:
            attempts.append({"engine": engine, "model": candidate_model, "ok": False, "error": "package not installed"})
            continue
        if engine == "openai-whisper" and importlib.util.find_spec("whisper") is None:
            attempts.append({"engine": engine, "model": candidate_model, "ok": False, "error": "package not installed"})
            continue
        try:
            result = transcribe_faster_whisper(audio_path, candidate_model, language) if engine == "faster-whisper" else transcribe_openai_whisper(audio_path, candidate_model, language)
            result["attempts"] = attempts + [{"engine": engine, "model": candidate_model, "ok": True}]
            return result
        except Exception as exc:  # noqa: BLE001
            attempts.append({"engine": engine, "model": candidate_model, "ok": False, "error": str(exc)})
    return {
        "ok": False,
        "engine": "none",
        "model": model,
        "segments": [],
        "attempts": attempts,
        "error": "No local STT fallback succeeded. Install/cache a local model or use an approved cloud STT path.",
    }


def split_audio(audio_path: Path, output_dir: Path, chunk_seconds: int) -> list[Path]:
    if not shutil.which("ffmpeg"):
        return [audio_path]
    pattern = output_dir / f"{audio_path.stem}.chunk_%03d.wav"
    proc = run_cmd(["ffmpeg", "-hide_banner", "-y", "-i", str(audio_path), "-f", "segment", "-segment_time", str(chunk_seconds), "-c", "copy", str(pattern)])
    chunks = sorted(output_dir.glob(f"{audio_path.stem}.chunk_*.wav"))
    return chunks if proc.returncode == 0 and chunks else [audio_path]


def choose_stt(audio_path: Path, model: str, language: str | None, transcript: Path | None, raw_fallbacks: str | None, chunk_minutes: float) -> dict[str, Any]:
    if transcript:
        result = read_transcript(transcript)
        result["attempts"] = [{"engine": "provided-transcript", "model": "none", "ok": True}]
        return result

    duration = probe_duration(audio_path)
    if duration and duration > chunk_minutes * 60 and shutil.which("ffmpeg"):
        temp_dir = Path(tempfile.mkdtemp(prefix="atm_chunks_"))
        chunk_paths = split_audio(audio_path, temp_dir, int(chunk_minutes * 60))
        all_segments: list[dict[str, Any]] = []
        chunk_reports = []
        offset = 0.0
        try:
            for idx, chunk_path in enumerate(chunk_paths):
                chunk_duration = probe_duration(chunk_path) or 0.0
                chunk_result = transcribe_with_fallback(chunk_path, model, language, raw_fallbacks)
                chunk_quality = assess_quality(chunk_result.get("segments", []), chunk_duration)
                chunk_reports.append(
                    {
                        "index": idx,
                        "path": str(chunk_path),
                        "duration_seconds": chunk_duration,
                        "engine": chunk_result.get("engine"),
                        "model": chunk_result.get("model"),
                        "ok": chunk_result.get("ok"),
                        "quality_status": chunk_quality.status,
                        "attempts": chunk_result.get("attempts", []),
                        "error": chunk_result.get("error"),
                    }
                )
                if chunk_result.get("ok") and chunk_quality.status != QUALITY_FAILED:
                    for segment in chunk_result.get("segments", []):
                        copied = dict(segment)
                        copied["start"] = float(copied.get("start", 0.0)) + offset
                        copied["end"] = float(copied.get("end", 0.0)) + offset
                        all_segments.append(copied)
                offset += chunk_duration
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
        ok_chunks = [chunk for chunk in chunk_reports if chunk.get("ok") and chunk.get("quality_status") != QUALITY_FAILED]
        return {
            "ok": bool(ok_chunks),
            "engine": "chunked-local-stt",
            "model": ok_chunks[-1].get("model") if ok_chunks else model,
            "language": language,
            "segments": all_segments,
            "chunks": chunk_reports,
            "attempts": [attempt for chunk in chunk_reports for attempt in chunk.get("attempts", [])],
            "error": None if ok_chunks else "All chunks failed STT quality gate or transcription.",
        }

    return transcribe_with_fallback(audio_path, model, language, raw_fallbacks)

