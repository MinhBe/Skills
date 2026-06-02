# Getting Started

## Installation

```bash
pip install -r requirements.txt
```

This installs:
- **easyocr** — Deep learning OCR engine (offline)
- **PyMuPDF** — PDF to image rendering
- **Pillow** — Image processing

## First Run (Model Download)

EasyOCR needs to download pre-trained models on first use (~100MB). After that, it works fully offline.

```bash
python scripts/ocr_processor.py --input sample.pdf
```

The model will be cached in `~/.EasyOCR/` and reused for all subsequent runs without internet.

## Verify It Works

```bash
python scripts/ocr_processor.py --input path/to/any.pdf
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `easyocr not installed` | Run `pip install easyocr` |
| `PyMuPDF not installed` | Run `pip install PyMuPDF` |
| OCR quality poor | Increase `--dpi` (e.g., 400) |
| Slow processing | Add `--gpu` if you have a CUDA GPU |
| Language not detected | Set `--lang vi` for Vietnamese, etc. |

## Next Steps

- See [guide.md](guide.md) for usage examples
- See [formats.md](formats.md) for output options
