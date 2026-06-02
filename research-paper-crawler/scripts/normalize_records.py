#!/usr/bin/env python3
"""Normalize and deduplicate scholarly metadata JSONL records."""

from __future__ import annotations

import argparse
import json
import re
from typing import Any, Dict, Iterable


SCHEMA_KEYS = [
    "id", "source", "title", "authors", "year", "doi", "abstract", "venue",
    "publisher", "document_type", "language", "countries", "affiliations",
    "keywords", "concepts", "citation_count", "is_open_access", "license",
    "url", "pdf_url", "source_record",
]


def normalize_doi(value: Any) -> str:
    if not value:
        return ""
    value = str(value).strip().lower()
    value = value.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return value


def normalize_title(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize(record: Dict[str, Any]) -> Dict[str, Any]:
    out = {key: record.get(key) for key in SCHEMA_KEYS}
    out["title"] = normalize_title(out["title"])
    out["doi"] = normalize_doi(out["doi"])
    out["authors"] = [str(v).strip() for v in ensure_list(out["authors"]) if str(v).strip()]
    out["countries"] = sorted({str(v).strip().upper() for v in ensure_list(out["countries"]) if str(v).strip()})
    out["affiliations"] = [str(v).strip() for v in ensure_list(out["affiliations"]) if str(v).strip()]
    out["keywords"] = [str(v).strip() for v in ensure_list(out["keywords"]) if str(v).strip()]
    out["concepts"] = [str(v).strip() for v in ensure_list(out["concepts"]) if str(v).strip()]
    return out


def dedupe(records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    seen = set()
    for record in records:
        doi = record.get("doi")
        title = " ".join((record.get("title") or "").lower().split())
        key = ("doi", doi) if doi else ("title-year", title, record.get("year"))
        if key in seen:
            continue
        seen.add(key)
        yield record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    with open(args.input, "r", encoding="utf-8") as src:
        records = [normalize(json.loads(line)) for line in src if line.strip()]
    with open(args.output, "w", encoding="utf-8") as dst:
        for record in dedupe(records):
            dst.write(json.dumps(record, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
