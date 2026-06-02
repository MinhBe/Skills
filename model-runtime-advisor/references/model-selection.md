# Model Selection Rules

Use these rules after running `scripts/inspect_runtime.py`.

## Speech-to-Text

| Host condition | Recommended path |
|---|---|
| NVIDIA GPU with 8 GB+ VRAM, CUDA visible, `faster_whisper` installed | `faster-whisper` `medium` or `large-v3` depending on language and speed needs |
| NVIDIA GPU with 4-8 GB VRAM | `faster-whisper` `small` or `medium` with int8/float16 compute |
| CPU-only with 16 GB+ RAM | Whisper/faster-whisper `base` or `small`; chunk long files |
| CPU-only with less than 16 GB RAM | `tiny`/`base` for short files; cloud recommended for long files |
| Missing `ffmpeg` | Install `ffmpeg` before reliable local STT, or use a cloud path that accepts the source format |

For Vietnamese or mixed-language audio, prefer `medium` or larger when hardware
allows it. If local resources are tight, use a smaller model and record quality
warnings in the final Markdown.

## Audio Length

- Under 30 minutes: local CPU can be acceptable with small models.
- 30-120 minutes: prefer GPU or cloud; CPU mode needs chunking and patience.
- Over 120 minutes: prefer GPU batch/chunk pipeline or cloud.

## Local LLMs

| VRAM/RAM | Guidance |
|---|---|
| 12 GB+ VRAM | 7B-13B quantized models are reasonable; larger models depend on quantization and context |
| 8 GB VRAM | 7B quantized models are realistic |
| CPU-only with 32 GB+ RAM | Small quantized local LLMs are possible but slower |
| CPU-only with less than 32 GB RAM | Cloud or remote inference is usually better |

## OCR/VLM

- Use native text extraction before OCR for digital PDFs.
- Use CPU OCR engines for simple scans.
- Use GPU/VLM OCR only when layout, handwriting, tables, or poor scans justify
  the cost.

## Recommendation Language

Use concrete wording:

- "Local-ready for faster-whisper small/medium" when dependencies and resources
  are present.
- "Local-limited" when local execution works but needs smaller models or chunking.
- "Cloud-recommended" when install gaps, low memory, no `ffmpeg`, or long files
  make local processing impractical.
