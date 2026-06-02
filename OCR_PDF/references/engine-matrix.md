# OCR Engine Matrix

Use this matrix after running `scripts/env_probe.py`.

| Engine | Best for | Strength | Cost/Risk |
|--------|----------|----------|-----------|
| PyMuPDF | Digital PDFs | Near-instant text extraction | Fails on image-only scans |
| Tesseract | Simple scans, CPU-only machines | Lightweight, mature, offline | Needs external binary; weaker layout |
| RapidOCR | Fast OCR on CPU | Good speed/quality balance | Less layout-aware |
| PaddleOCR | General OCR, multilingual documents | Strong detector/recognizer ecosystem | Heavier install |
| EasyOCR | Offline fallback, common languages | Already simple to use | Slow on long PDFs |
| Surya | Layout, reading order, tables | Strong document understanding | Heavier model path |
| Marker | PDF-to-Markdown | Uses OCR only where needed; layout-aware | Heavy dependencies |
| docTR | Deep-learning OCR pipelines | Good detector/recognizer framework | Needs integration work |
| Nougat | Scientific papers/math | Markdown/LaTeX-oriented | Narrow domain |
| olmOCR | Difficult PDF/image documents | High-quality VLM OCR | GPU/model-heavy |

Default preference:

1. PyMuPDF for pages with usable text.
2. Marker/Surya for Markdown/layout-heavy requests.
3. PaddleOCR/RapidOCR for general scanned pages.
4. Tesseract for lightweight CPU fallback.
5. EasyOCR as the broad installed fallback.
