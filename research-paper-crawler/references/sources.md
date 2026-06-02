# Source Selection

Prefer sources with APIs, stable metadata, and clear access rules.

| Source | Best use | Notes |
| --- | --- | --- |
| OpenAlex | Broad global discovery, affiliation filtering, concepts, citations | Primary default source |
| Crossref | DOI metadata, publisher records, journal/conference metadata | Good DOI fallback, abstract coverage varies |
| Semantic Scholar | CS/AI coverage, citation and abstract enrichment | Respect API limits; API key improves throughput |
| arXiv | Preprints in CS, math, physics, quantitative fields | Strong for AI/security preprints |
| PubMed | Biomedical and life-science literature | Use for health, medicine, biosecurity |
| Europe PMC | Biomedical Europe-focused and global metadata | Useful for Europe and open-access links |
| DOAJ | Open-access journals | Useful when user asks for OA-only |
| CORE | Repository and full-text metadata | Useful for open repository discovery |
| DataCite | Datasets, software, reports, DOI objects | Use for research artifacts |
| HAL | French and European open archive | Use for Europe/French institutional material |
| Zenodo | European research outputs and datasets | Use for OA artifacts |
| J-STAGE | Japanese journals | Use for Japan-specific discovery |
| CiNii Research | Japanese academic metadata | Use when Japan coverage matters |
| KoreaScience/KCI/KISTI | Korean literature | Use when Korean local coverage matters and access permits |
| CyberLeninka | Russian open-access articles | Use for Russia, respecting robots and terms |
| Shodhganga | Indian theses | Use for thesis-focused India searches |

## Restricted Or Sensitive Sources

CNKI, Wanfang, eLIBRARY/RSCI, and some publisher portals can be valuable but may
block automation, require login, or restrict scraping. Do not bypass these
controls. Use them only through official exports, permitted APIs, institutional
access, or manual user-provided files.

## Fallback Order

1. OpenAlex for broad discovery and regional filtering.
2. Crossref for DOI and publisher metadata.
3. Domain-specific API for the field.
4. Country repository or national index if access is permitted.
5. User-provided exported files or PDFs.
