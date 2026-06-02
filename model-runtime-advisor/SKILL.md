---
name: model-runtime-advisor
description: Inspect the local machine and advise whether model workloads should run locally or use cloud APIs. Use when the user asks whether their computer can run Whisper, faster-whisper, local LLMs, OCR/VLM models, CUDA/GPU workloads, or wants a hardware, Python, ffmpeg, STT engine, model cache, and runtime readiness report before choosing a pipeline.
---

# Model Runtime Advisor

Probe first, recommend second. Do not guess from memory when the local machine
can be inspected.

## Workflow

1. Run `scripts/inspect_runtime.py` unless the user only wants static guidance.
2. Review CPU, RAM, disk, OS, Python, CUDA/GPU/VRAM, `nvidia-smi`, `ffmpeg`,
   known Python packages, and model caches.
3. Classify the host as:
   - `local-ready`: GPU/VRAM or CPU/RAM are sufficient for the requested model.
   - `local-limited`: local execution is possible but should use smaller models,
     quantization, chunking, or slower CPU mode.
   - `cloud-recommended`: missing dependencies or insufficient resources make
     cloud execution more practical.
4. Read `references/model-selection.md` when choosing STT, OCR, VLM, or local
   LLM model sizes.
5. Use `assets/runtime-report-template.md` as the report structure when the user
   asks for a written recommendation.

## Commands

```powershell
python Skill\model-runtime-advisor\scripts\inspect_runtime.py
python Skill\model-runtime-advisor\scripts\inspect_runtime.py --output-md runtime-advisor-report.md --output-json runtime-advisor-report.json
python Skill\model-runtime-advisor\scripts\inspect_runtime.py --workload stt --audio-minutes 90
```

## Decision Rules

- Prefer local STT with `faster-whisper` when CUDA and enough VRAM are present.
- Prefer CPU Whisper base/small only for short or medium audio when RAM is
  adequate and the user accepts slower runtime.
- Recommend cloud STT for long audio on weak CPU-only machines, missing
  `ffmpeg`, or when accuracy/turnaround matters more than offline execution.
- Treat cache detection as best-effort. Missing cache folders are not errors.
- State uncertainty clearly: hardware probes are capability estimates, not a
  benchmark.

## Output Expectations

Return a concise report with:

- Runtime verdict and why.
- Available accelerators and dependencies.
- Existing model/cache hints.
- Recommended pipeline, model size, and fallback.
- Missing installs only when they are directly useful for the requested task.
