---
name: mistral-ocr
description: >-
  Convert PDFs and images into readable text or Markdown with an adaptive local
  OCR router. Use this skill whenever the user needs to read, OCR, digitize,
  batch-convert, or extract Markdown/text from PDFs, scanned documents, images,
  research papers, tables, or mixed digital/scanned files. The skill should
  first probe the machine, detect available OCR engines, classify the document,
  and choose the fastest reliable path before asking the user to install any
  missing engine.
compatibility: python3, PyMuPDF, Pillow, optional OCR engines
---

# OCR PDF Adaptive Router

Local-first PDF/image OCR and PDF-to-Markdown workflow. Prefer fast native text
extraction when it is good enough, OCR only the pages that need it, and escalate
to stronger engines only when the document requires them.

## Operating Principle

Do not ask the user what is installed. Probe the machine first, summarize what
is available, then ask for installation only when a missing engine would improve
the requested output.

Default workflow:

1. Run `..\model-runtime-advisor\scripts\inspect_runtime.py --workload ocr`
   for machine-level readiness: Python, CPU/RAM, disk, GPU/CUDA, `ffmpeg`,
   model caches, and local model feasibility.
2. Run `scripts/env_probe.py` only for OCR-specific engine availability:
   PyMuPDF, OCR packages, Tesseract binary, and OCR model cache hints.
3. Inspect the input document. For PDFs, detect per-page text layer quality and
   whether pages are likely scanned/image-heavy.
4. Route each page through the cheapest reliable path:
   - Native text extraction for digital pages.
   - OCR only for pages with missing or poor text.
   - Layout/Markdown engines for complex documents.
5. Validate output length and quality. Retry weak pages with a stronger engine,
   higher DPI, or a layout-aware profile.
6. Cache page results by file hash, page, DPI, language, engine, and profile so
   reruns do not repeat expensive OCR.

## Modes

| Mode | Purpose | Typical Engine |
|------|---------|----------------|
| `auto` | Default balanced routing | PyMuPDF + best installed OCR fallback |
| `native` | Digital PDFs with good text layer | PyMuPDF |
| `scan-fast` | Fast OCR on simple scans | RapidOCR/Tesseract/EasyOCR |
| `balanced` | Better OCR without maximum cost | PaddleOCR/RapidOCR/EasyOCR |
| `quality` | Difficult scans or dense text | PaddleOCR/EasyOCR/Surya |
| `markdown` | Readable Markdown with layout | Marker/Surya |
| `scientific` | Papers, formulas, LaTeX-heavy PDFs | Nougat/Marker |
| `vlm-quality` | Hard documents when GPU is available | olmOCR or a VLM OCR path |
| `fast` | Backward-compatible alias for `native` | PyMuPDF |
| `max` | Backward-compatible alias for `quality` | EasyOCR/PaddleOCR |

Use `auto` unless the user explicitly asks for a specific profile.

## Engine Preference

Choose engines in this order when available:

1. `PyMuPDF` for digital PDF text layers.
2. `Marker` or `Surya` for PDF-to-Markdown, layout, reading order, tables, or
   mixed content.
3. `PaddleOCR` or `RapidOCR` for fast general OCR.
4. `Tesseract` for lightweight CPU fallback and simple scans.
5. `EasyOCR` for robust offline fallback and languages supported by local
   models.
6. `Nougat` for scientific PDFs.
7. `olmOCR` for high-quality VLM OCR when installed and hardware allows it.

If a preferred engine is missing, continue with the best installed engine. Ask
to install only if the installed path is likely to be too slow or low quality
for the user's task.

## Usage

```bash
# Machine/runtime readiness, delegated to model-runtime-advisor
python ..\model-runtime-advisor\scripts\inspect_runtime.py --workload ocr

# Probe installed engines and hardware
python scripts/env_probe.py

# Adaptive default
python scripts/ocr_router.py --input paper.pdf --output paper.md

# Force Markdown/layout profile
python scripts/ocr_router.py --input paper.pdf --output paper.md --mode markdown

# Backward-compatible legacy processor
python scripts/ocr_processor.py --input paper.pdf --output paper.md --mode fast
```

### Flags

| Flag | Description |
|------|-------------|
| `--input` / `-i` | Path to PDF, PNG, JPG, JPEG, WEBP, GIF |
| `--output` / `-o` | Output `.md`/`.txt` file (default: stdout) |
| `--mode` | `auto`, `native`, `scan-fast`, `balanced`, `quality`, `markdown`, `scientific`, `vlm-quality`, `fast`, `max` |
| `--lang` | Language code(s), comma-separated (default: `en`) |
| `--dpi` | Override auto DPI |
| `--page-separator` | Text between pages (default: `---`) |
| `--include-images` | Save rendered PDF pages as PNG |
| `--gpu` | Prefer GPU-capable engines when available |
| `--pages` | Page subset such as `1,2,5-8` |
| `--no-cache` | Disable page cache |

## Installation Policy

Base dependencies are in `requirements.txt`. Optional heavy engines are in
`requirements-optional.txt`.

Install flow:

1. Run `python ..\model-runtime-advisor\scripts\inspect_runtime.py --workload ocr`.
2. Run `python scripts/env_probe.py`.
3. Compare installed engines with the requested task.
4. If a missing engine is useful, ask the user before installing. State the
   package names and that model downloads may occur.
5. After installation, run both probes again and report what changed.

## Error Detection

The router detects problems and writes logs beside the output:

| Error Type | Meaning |
|------------|---------|
| `exception` | File corrupt, encrypted, or unreadable |
| `empty_output` | OCR returned no text at all |
| `output_too_short` | Very little text extracted |
| `weak_page` | A page produced suspiciously little or noisy text |
| `engine_missing` | Best engine for the requested mode is not installed |

## Batch Pipeline

```powershell
foreach ($pdf in Get-ChildItem "*.pdf") {
  python scripts/ocr_router.py --input $pdf.FullName --output "out/$($pdf.BaseName).md" --mode auto
}
```

## References

- Read `references/engine-matrix.md` when choosing an engine.
- Read `references/install-policy.md` before installing optional engines.
- Read `references/auto-mode.md` for the adaptive routing algorithm.
- Read `references/pdf-to-markdown.md` for Markdown-specific conversion.
