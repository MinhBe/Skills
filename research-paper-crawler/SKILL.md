---
name: research-paper-crawler
description: Find, crawl, normalize, and export scholarly paper metadata across Europe, Russia, India, Canada, Japan, the United States, the United Kingdom, China, and Korea. Use when Codex needs to discover scientific literature, build a regional research corpus, collect DOI/title/abstract/author/affiliation/open-access metadata, check legal crawl constraints, or export paper search results as JSONL, CSV, Markdown, BibTeX, or RIS.
---

# Research Paper Crawler

Find scholarly papers with API-first, policy-aware collection. Prefer structured
scholarly indexes over HTML scraping, and treat direct crawling as a fallback
only when the site permits it.

## Workflow

1. Clarify the user's topic, target regions, year range, document type, output
   format, and whether open-access PDF links are required.
2. Read `references/country_region_mapping.md` when mapping region names,
   country aliases, or affiliation filters.
3. Read `references/sources.md` before choosing sources. Use broad indexes
   first: OpenAlex, Crossref, Semantic Scholar, arXiv, PubMed, Europe PMC,
   DataCite, DOAJ, and CORE.
4. Read `references/query_patterns.md` when expanding multilingual or
   field-specific search terms.
5. Run `scripts/search_papers.py` for OpenAlex/Crossref metadata collection.
6. Run `scripts/fetch_metadata.py` when DOI-level enrichment is needed.
7. Run `scripts/normalize_records.py` before merging records from several
   sources.
8. Run `scripts/export_results.py` to produce JSONL, CSV, Markdown, BibTeX, or
   RIS.
9. Read `references/crawl_policy.md` and run `scripts/robots_check.py` before
   crawling any non-API web page or downloading PDFs.

## Commands

```powershell
python Skill\research-paper-crawler\scripts\search_papers.py --query "SQL injection detection GAN" --regions us,uk,china --from-year 2020 --to-year 2026 --max-results 100 --output papers.jsonl
python Skill\research-paper-crawler\scripts\fetch_metadata.py --input papers.jsonl --output papers.enriched.jsonl
python Skill\research-paper-crawler\scripts\normalize_records.py --input papers.enriched.jsonl --output papers.normalized.jsonl
python Skill\research-paper-crawler\scripts\export_results.py --input papers.normalized.jsonl --format md --output papers.md
python Skill\research-paper-crawler\scripts\robots_check.py https://example.edu/repository/paper
```

## Defaults

- Use `openalex,crossref` unless the task clearly needs a domain-specific
  source.
- Use metadata-only collection unless the user explicitly asks for PDFs.
- Download or link PDFs only when they are clearly public/open access.
- Do not bypass paywalls, CAPTCHA, authentication, geographic restrictions, or
  publisher anti-bot controls.
- Respect robots.txt, rate limits, and source terms. If a source is restricted,
  report the limitation and use Crossref/OpenAlex/Semantic Scholar metadata as
  fallback.
- Deduplicate by DOI first, then normalized title and year.
- Keep uncertainty explicit: affiliation country and study country are not the
  same thing unless the source states both.

## Output Expectations

Return a concise search report with:

- Query terms and filters used.
- Sources queried and any access limitations.
- Count by country/region and source.
- Deduplication method.
- Output file paths and format.
- Coverage gaps, especially for Russia, China, Korea, Japan, and India where
  local databases may limit automated access.
