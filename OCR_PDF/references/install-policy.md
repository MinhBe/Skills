# Installation Policy

Probe first. Do not ask the user what is installed.

1. Run `python scripts/env_probe.py`.
2. If the requested task can be completed well with installed tools, continue.
3. If an optional engine would materially improve speed or quality, ask before
   installing it.
4. In the prompt, name the package, explain why it is useful, and mention model
   or binary downloads.
5. Re-run `env_probe.py` after installation and report the changed status.

Recommended optional package groups:

```bash
# Fast CPU OCR
pip install pytesseract rapidocr-onnxruntime

# Strong general OCR
pip install paddleocr

# Document layout / Markdown
pip install surya-ocr marker-pdf

# Deep-learning OCR framework
pip install "python-doctr[torch]"
```

Tesseract also needs the external Tesseract executable on Windows. The Python
package `pytesseract` is only a wrapper.
