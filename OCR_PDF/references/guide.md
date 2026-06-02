# Step-by-Step Guide

## Installation

```bash
pip install -r requirements.txt
```

## Two Modes

| Mode | DPI | Paragraph | Speed | Quality |
|------|-----|-----------|-------|---------|
| `--mode fast` | 150 | No | **3-5x faster** | Good |
| `--mode max` | 300 | Yes | Standard | **Best** |

Fast is default. Use max only when fast gives poor results.

## Basic Usage

### PDF to Text (Fast)

```bash
python scripts/ocr_processor.py --input paper.pdf --output paper.md
```

### PDF to Text (Max quality)

```bash
python scripts/ocr_processor.py --input paper.pdf --output paper.md --mode max
```

### Image to Text (stdout)

```bash
python scripts/ocr_processor.py --input scan.png
```

### Vietnamese Document

```bash
python scripts/ocr_processor.py --input vanban.pdf --lang vi --output output.md --mode max
```

### Override DPI

```bash
python scripts/ocr_processor.py --input old_scan.pdf --mode max --dpi 400 --output scan.md
```

### Extract Page Images

```bash
python scripts/ocr_processor.py --input doc.pdf --output doc.md --include-images
```

### GPU Acceleration

```bash
python scripts/ocr_processor.py --input doc.pdf --output doc.md --gpu
```

## Batch Processing (Fast → Error → Max)

Recommended pipeline for bulk OCR:

```powershell
mkdir -p output

# Step 1: Fast mode for everything
foreach ($pdf in Get-ChildItem -Filter "*.pdf") {
  $out = "output/$($pdf.BaseName).md"
  python scripts/ocr_processor.py --input $pdf.FullName --output $out --mode fast
}

# Step 2: Check errors
$errorFile = "output/ocr_errors.json"
if (Test-Path $errorFile) {
  $errors = Get-Content $errorFile | ConvertFrom-Json
  Write-Host "Retrying $($errors.Count) failed files with --mode max..."

  foreach ($e in $errors) {
    $out = "output/$($e.file -replace '.pdf','.md' -replace '.png','.md')"
    Write-Host "  Retry: $($e.file) (error: $($e.error_type))"
    python scripts/ocr_processor.py --input $e.path --output $out --mode max
  }

  # Step 3: Archive retried errors
  Move-Item $errorFile "output/ocr_errors_retried.json" -Force
}
```

## Best Results

1. **Fast first, max on demand** — batch with fast, retry failures with max
2. **Language** — always set `--lang` for non-English docs
3. **DPI** — override with `--dpi 400` only when needed
4. **GPU** — `--gpu` speeds up processing 5-10x

## Next Steps

- See [formats.md](formats.md) for output options
- See [pdf-to-markdown.md](pdf-to-markdown.md) for PDF tips
