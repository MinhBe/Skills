#!/usr/bin/env python3
"""Inspect local runtime capability for model workloads.

The script is intentionally non-destructive: it reads system information,
checks executable/package availability, and writes optional JSON/Markdown
reports. It does not install packages or download models.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


STT_PACKAGES = [
    "faster_whisper",
    "whisper",
    "openai",
    "torch",
    "torchaudio",
    "speechbrain",
    "pyannote.audio",
]

MODEL_TOOLS = ["ollama", "ffmpeg", "nvidia-smi"]


def run_command(cmd: list[str], timeout: int = 8) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:  # noqa: BLE001 - diagnostics should not crash
        return {"ok": False, "error": str(exc)}


def bytes_to_gib(value: int | None) -> float | None:
    if value is None:
        return None
    return round(value / (1024**3), 2)


def memory_info() -> dict[str, Any]:
    if platform.system().lower() == "windows":
        ps = run_command(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory",
            ]
        )
        if ps.get("ok"):
            try:
                total = int(ps["stdout"].splitlines()[-1].strip())
                return {"total_gib": bytes_to_gib(total)}
            except Exception:
                pass
    try:
        import psutil  # type: ignore

        vm = psutil.virtual_memory()
        return {"total_gib": bytes_to_gib(int(vm.total)), "available_gib": bytes_to_gib(int(vm.available))}
    except Exception:
        return {"total_gib": None}


def cpu_info() -> dict[str, Any]:
    name = platform.processor() or platform.machine()
    if platform.system().lower() == "windows":
        ps = run_command(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)",
            ]
        )
        if ps.get("ok") and ps.get("stdout"):
            name = ps["stdout"].splitlines()[-1].strip()
    return {"name": name, "logical_cores": os.cpu_count()}


def disk_info(path: Path) -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(path)
        return {
            "path": str(path),
            "total_gib": bytes_to_gib(usage.total),
            "free_gib": bytes_to_gib(usage.free),
        }
    except Exception as exc:
        return {"path": str(path), "error": str(exc)}


def package_status(names: list[str]) -> dict[str, bool]:
    status = {}
    for name in names:
        try:
            status[name] = importlib.util.find_spec(name) is not None
        except ModuleNotFoundError:
            status[name] = False
    return status


def executable_status(names: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for name in names:
        path = shutil.which(name)
        out[name] = {"available": bool(path), "path": path}
    return out


def parse_nvidia_smi() -> dict[str, Any]:
    if not shutil.which("nvidia-smi"):
        return {"available": False, "gpus": []}
    query = [
        "nvidia-smi",
        "--query-gpu=name,memory.total,driver_version",
        "--format=csv,noheader,nounits",
    ]
    result = run_command(query)
    gpus = []
    if result.get("ok"):
        for line in result.get("stdout", "").splitlines():
            parts = [part.strip() for part in line.split(",")]
            if len(parts) >= 3:
                try:
                    vram_gib = round(float(parts[1]) / 1024, 2)
                except ValueError:
                    vram_gib = None
                gpus.append({"name": parts[0], "vram_gib": vram_gib, "driver": parts[2]})
    return {"available": True, "gpus": gpus, "raw": result}


def torch_cuda_status() -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {"torch_installed": False, "cuda_available": False}
    try:
        import torch  # type: ignore

        devices = []
        if torch.cuda.is_available():
            for idx in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(idx)
                devices.append({"name": props.name, "vram_gib": bytes_to_gib(int(props.total_memory))})
        return {
            "torch_installed": True,
            "torch_version": getattr(torch, "__version__", None),
            "cuda_available": bool(torch.cuda.is_available()),
            "cuda_version": getattr(torch.version, "cuda", None),
            "devices": devices,
        }
    except Exception as exc:
        return {"torch_installed": True, "cuda_available": False, "error": str(exc)}


def ffmpeg_status() -> dict[str, Any]:
    path = shutil.which("ffmpeg")
    if not path:
        return {"available": False}
    result = run_command(["ffmpeg", "-version"], timeout=5)
    first_line = result.get("stdout", "").splitlines()[0] if result.get("stdout") else ""
    return {"available": True, "path": path, "version": first_line}


def model_cache_hints() -> list[dict[str, Any]]:
    home = Path.home()
    env_paths = [
        os.environ.get("HF_HOME"),
        os.environ.get("TRANSFORMERS_CACHE"),
        os.environ.get("XDG_CACHE_HOME"),
    ]
    candidates = [
        home / ".cache" / "huggingface",
        home / ".cache" / "whisper",
        home / ".cache" / "torch",
        home / ".cache" / "faster-whisper",
        home / ".ollama" / "models",
        Path(os.environ.get("USERPROFILE", str(home))) / ".cache" / "huggingface",
        Path(os.environ.get("LOCALAPPDATA", str(home))) / "huggingface",
    ]
    for raw in env_paths:
        if raw:
            candidates.append(Path(raw))

    seen: set[str] = set()
    hints = []
    for path in candidates:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        exists = path.exists()
        item: dict[str, Any] = {"path": str(path), "exists": exists}
        if exists:
            try:
                children = list(path.iterdir())[:20]
                item["sample_entries"] = [child.name for child in children]
            except Exception as exc:
                item["error"] = str(exc)
        hints.append(item)
    return hints


def classify(report: dict[str, Any], workload: str, audio_minutes: float | None) -> dict[str, Any]:
    ram = report["memory"].get("total_gib") or 0
    gpus = report["gpu"].get("nvidia_smi", {}).get("gpus", [])
    max_vram = max([gpu.get("vram_gib") or 0 for gpu in gpus], default=0)
    ffmpeg = report["dependencies"]["ffmpeg"]["available"]
    packages = report["python"]["packages"]
    has_stt = packages.get("faster_whisper") or packages.get("whisper")

    reasons = []
    missing = []
    if not ffmpeg and workload in {"stt", "audio", "ocr"}:
        missing.append("ffmpeg")
        reasons.append("ffmpeg is missing, so media normalization/conversion is limited")
    if workload in {"stt", "audio"} and not has_stt:
        missing.append("local STT package such as faster-whisper or whisper")
        reasons.append("no local STT package was detected")

    classification = "local-limited"
    recommendation = "Use local lightweight models with chunking, or use cloud for speed."

    if workload in {"stt", "audio"}:
        long_audio = audio_minutes is not None and audio_minutes > 120
        if max_vram >= 8 and ffmpeg and has_stt:
            classification = "local-ready"
            recommendation = "Use faster-whisper small/medium locally; consider large-v3 if VRAM and speed allow."
            reasons.append(f"detected GPU VRAM around {max_vram} GiB")
        elif max_vram >= 4 and ffmpeg and has_stt:
            classification = "local-ready"
            recommendation = "Use faster-whisper small or medium with int8/float16 compute."
            reasons.append(f"detected GPU VRAM around {max_vram} GiB")
        elif ram >= 16 and ffmpeg and has_stt and not long_audio:
            classification = "local-limited"
            recommendation = "Use CPU Whisper/faster-whisper base or small; chunk files longer than 30 minutes."
            reasons.append(f"detected RAM around {ram} GiB")
        else:
            classification = "cloud-recommended"
            recommendation = "Use cloud STT or install missing local dependencies before retrying locally."
    elif max_vram >= 8 or ram >= 32:
        classification = "local-ready"
        recommendation = "Local quantized models are reasonable; benchmark the exact model before committing."
        reasons.append("memory/VRAM is adequate for many small or quantized models")
    elif ram < 16 and max_vram < 4:
        classification = "cloud-recommended"
        recommendation = "Prefer cloud or remote inference for non-trivial model workloads."
        reasons.append("low RAM/VRAM for model workloads")

    return {
        "classification": classification,
        "recommendation": recommendation,
        "reasons": reasons or ["capability estimated from detected hardware and dependencies"],
        "missing": missing,
    }


def collect_report(workload: str, audio_minutes: float | None) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema_version": 1,
        "workload": workload,
        "audio_minutes": audio_minutes,
        "system": {
            "os": platform.platform(),
            "machine": platform.machine(),
            "python_executable": sys.executable,
        },
        "cpu": cpu_info(),
        "memory": memory_info(),
        "disk": disk_info(Path.cwd()),
        "python": {
            "version": sys.version.split()[0],
            "packages": package_status(STT_PACKAGES + ["transformers", "accelerate", "ctranslate2"]),
        },
        "executables": executable_status(MODEL_TOOLS),
        "dependencies": {"ffmpeg": ffmpeg_status()},
        "gpu": {"nvidia_smi": parse_nvidia_smi(), "torch_cuda": torch_cuda_status()},
        "model_caches": model_cache_hints(),
    }
    report["verdict"] = classify(report, workload, audio_minutes)
    return report


def markdown_report(report: dict[str, Any]) -> str:
    verdict = report["verdict"]
    packages = report["python"]["packages"]
    caches = [cache for cache in report["model_caches"] if cache.get("exists")]
    gpu_names = [
        f"{gpu.get('name')} ({gpu.get('vram_gib')} GiB)"
        for gpu in report["gpu"]["nvidia_smi"].get("gpus", [])
    ]
    lines = [
        "# Runtime Advisor Report",
        "",
        "## Verdict",
        "",
        f"- Classification: `{verdict['classification']}`",
        f"- Recommendation: {verdict['recommendation']}",
        f"- Reasons: {'; '.join(verdict['reasons'])}",
        "",
        "## Machine",
        "",
        f"- OS: {report['system']['os']}",
        f"- CPU: {report['cpu'].get('name')} ({report['cpu'].get('logical_cores')} logical cores)",
        f"- RAM: {report['memory'].get('total_gib')} GiB",
        f"- Disk free: {report['disk'].get('free_gib')} GiB at {report['disk'].get('path')}",
        f"- Python: {report['python']['version']} at {report['system']['python_executable']}",
        "",
        "## Accelerators",
        "",
        f"- GPU: {', '.join(gpu_names) if gpu_names else 'not detected'}",
        f"- Torch CUDA: {report['gpu']['torch_cuda'].get('cuda_available')}",
        "",
        "## Dependencies",
        "",
        f"- ffmpeg: {report['dependencies']['ffmpeg'].get('available')}",
        f"- STT packages: {', '.join([name for name in STT_PACKAGES if packages.get(name)]) or 'none detected'}",
        "",
        "## Model Cache Hints",
        "",
    ]
    if caches:
        lines.extend([f"- {cache['path']}: {', '.join(cache.get('sample_entries', [])[:5])}" for cache in caches])
    else:
        lines.append("- No known cache folders detected.")
    lines.extend(["", "## Missing Items", ""])
    missing = verdict.get("missing") or []
    lines.extend([f"- {item}" for item in missing] if missing else ["- None critical for the current recommendation."])
    lines.extend(["", "## Caveats", "", "- This is a capability estimate, not a benchmark."])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect local runtime capability for model workloads.")
    parser.add_argument("--workload", default="stt", choices=["stt", "audio", "ocr", "llm", "general"])
    parser.add_argument("--audio-minutes", type=float, default=None)
    parser.add_argument("--output-json", default=None)
    parser.add_argument("--output-md", default=None)
    args = parser.parse_args()

    report = collect_report(args.workload, args.audio_minutes)
    if args.output_json:
        Path(args.output_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.output_md:
        Path(args.output_md).write_text(markdown_report(report), encoding="utf-8")
    print(markdown_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
