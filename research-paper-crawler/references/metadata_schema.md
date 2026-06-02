# Metadata Schema

Normalize records to these fields.

```json
{
  "id": "",
  "source": "",
  "title": "",
  "authors": [],
  "year": null,
  "doi": "",
  "abstract": "",
  "venue": "",
  "publisher": "",
  "document_type": "",
  "language": "",
  "countries": [],
  "affiliations": [],
  "keywords": [],
  "concepts": [],
  "citation_count": null,
  "is_open_access": null,
  "license": "",
  "url": "",
  "pdf_url": "",
  "source_record": {}
}
```

## Normalization Rules

- Lowercase DOI and strip `https://doi.org/`.
- Preserve author order.
- Store countries as ISO alpha-2 codes when available.
- Keep source-specific raw data in `source_record` only when needed for audit.
- Deduplicate by DOI first. If DOI is missing, use normalized title plus year.
- Do not invent abstracts, affiliations, licenses, or PDF URLs.
