# PDF to Text

The OCR processor handles PDFs directly by rendering each page to an image and running local OCR.

## Quick Example

```bash
python scripts/ocr_processor.py --input document.pdf --output document.md
```

## How It Works

1. PyMuPDF renders each PDF page to a PNG image (at specified DPI)
2. EasyOCR extracts text from each image
3. Results are combined with page separators

## Multi-Page Documents

All pages are processed and combined automatically.

```bash
python scripts/ocr_processor.py --input 100page.pdf --output full.md
```

Default separator between pages: `\n\n---\n\n`

Custom separator:
```bash
python scripts/ocr_processor.py --input doc.pdf --output doc.md --page-separator "\n\n## Page Break\n\n"
```

## Quality Tips

| Issue | Solution |
|-------|----------|
| Blurry/missing text | Increase `--dpi` to 400 |
| Wrong characters | Set correct `--lang` |
| Very slow | Add `--gpu` flag |
| Page images wanted | Add `--include-images` |

## Tips

- **Scanned PDFs** work directly — no preprocessing needed
- **Digital PDFs** (text-based) are also rendered and OCR'd
- **DPI** controls quality vs speed: 200 (fast), 300 (balanced), 400+ (best quality)
- For image-only files (PNG, JPG), the script processes them directly without PDF rendering
