#!/usr/bin/env python3
"""Enrich JSONL records with Crossref DOI metadata when a DOI is available."""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from typing import Any, Dict


def get_json(url: str, user_agent: str) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def normalize_doi(value: str) -> str:
    return value.strip().lower().replace("https://doi.org/", "").replace("http://doi.org/", "")


def enrich(record: Dict[str, Any], user_agent: str, email: str) -> Dict[str, Any]:
    doi = normalize_doi(record.get("doi") or "")
    if not doi:
        return record
    params = {}
    if email:
        params["mailto"] = email
    query = ("?" + urllib.parse.urlencode(params)) if params else ""
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="") + query
    data = get_json(url, user_agent)
    message = data.get("message") or {}
    record.setdefault("enrichment", {})
    record["enrichment"]["crossref"] = message
    if not record.get("publisher"):
        record["publisher"] = message.get("publisher", "")
    if not record.get("venue"):
        record["venue"] = (message.get("container-title") or [""])[0]
    if not record.get("url"):
        record["url"] = message.get("URL", "")
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--email", default="")
    parser.add_argument("--user-agent", default="research-paper-crawler/1.0 (mailto:research@example.local)")
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()
    with open(args.input, "r", encoding="utf-8") as src, open(args.output, "w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            record = json.loads(line)
            try:
                record = enrich(record, args.user_agent, args.email)
            except Exception as exc:  # keep batch runs useful when one DOI fails
                record.setdefault("errors", []).append(f"crossref enrichment failed: {exc}")
            dst.write(json.dumps(record, ensure_ascii=False) + "\n")
            time.sleep(args.delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
