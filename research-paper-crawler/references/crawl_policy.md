# Crawl Policy

Use API-first collection. Crawl HTML or download files only when allowed.

## Required Checks

1. Check robots.txt for non-API URLs with `scripts/robots_check.py`.
2. Review visible terms of use when the site is a publisher, database, or
   national index.
3. Use conservative delays and small batches.
4. Identify the client with a clear user agent when a script supports it.
5. Keep logs of source, query, time, and access decision.

## Do Not Do

- Do not bypass paywalls, login screens, CAPTCHA, rate limits, IP blocks, or
  geo-restrictions.
- Do not scrape publisher full text when metadata APIs are enough.
- Do not bulk-download PDFs unless license and source policy allow it.
- Do not present linked PDFs as open access unless the source clearly marks them
  public or open.

## Safe Fallbacks

- Use metadata-only records.
- Use DOI links instead of PDF downloads.
- Ask the user to provide institutional exports, CSV/BibTeX/RIS, or PDFs when a
  database is restricted.
