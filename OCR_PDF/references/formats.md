# Output Formats

The OCR processor extracts raw text from documents. Post-processing determines the final format.

## Default: Plain Text per Page

Extracted text is returned as-is from EasyOCR, one paragraph per detected text block per page.

### Example Output
```
Company Invoice

Invoice Number: INV-2026-001
Date: January 15, 2026

Bill To:
John Smith
123 Main Street
New York, NY 10001

Items:
Consulting Services — 10 hours — $1,500.00
Software License — 1 year — $299.00

Total: $1,799.00
```

## Markdown (Post-processed)

The model can structure plain OCR output into Markdown.

### Example
```markdown
# Company Invoice

**Invoice Number:** INV-2026-001
**Date:** January 15, 2026
```

## Structured JSON (Post-processed)

After OCR extraction, the model can parse text into structured JSON.

### Example
```json
{
  "invoice_number": "INV-2026-001",
  "date": "2026-01-15",
  "total": 1799.00,
  "items": [
    {"description": "Consulting Services", "amount": 1500.00}
  ]
}
```

## Format Comparison

| Format | Best For | How to Get |
|--------|----------|------------|
| **Plain Text** | Raw extraction | Default output |
| **Markdown** | Readable documents | Ask the model to format |
| **JSON** | Structured data | Ask the model to parse |

## Tips for Better Results

1. **Use high DPI** — `--dpi 400` for small or dense text
2. **Multi-page handled automatically** — pages separated by `---`
3. **Post-process as needed** — model can convert to Markdown/JSON
4. **Language matters** — use `--lang` for non-English documents
