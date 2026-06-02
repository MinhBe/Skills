#!/usr/bin/env python3
"""Search OpenAlex and Crossref and write normalized JSONL records."""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterable, List, Optional


REGION_COUNTRIES = {
    "us": ["US"],
    "usa": ["US"],
    "uk": ["GB"],
    "united-kingdom": ["GB"],
    "canada": ["CA"],
    "india": ["IN"],
    "japan": ["JP"],
    "china": ["CN"],
    "korea": ["KR"],
    "south-korea": ["KR"],
    "russia": ["RU"],
    "eu": [
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    ],
    "europe": [
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE", "GB", "CH", "NO",
        "IS", "UA",
    ],
}


def get_json(url: str, user_agent: str, timeout: int = 30) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def split_regions(value: str) -> List[str]:
    if not value:
        return []
    return [part.strip().lower() for part in value.split(",") if part.strip()]


def countries_for_regions(regions: Iterable[str]) -> List[str]:
    countries: List[str] = []
    for region in regions:
        countries.extend(REGION_COUNTRIES.get(region, [region.upper()]))
    return sorted(set(countries))


def abstract_from_inverted_index(index: Optional[Dict[str, List[int]]]) -> str:
    if not index:
        return ""
    positions = []
    for word, offsets in index.items():
        for offset in offsets:
            positions.append((offset, word))
    return " ".join(word for _, word in sorted(positions))


def normalize_doi(value: Optional[str]) -> str:
    if not value:
        return ""
    value = value.strip().lower()
    value = value.replace("https://doi.org/", "").replace("http://doi.org/", "")
    return value


def normalize_openalex(item: Dict[str, Any]) -> Dict[str, Any]:
    authors = []
    affiliations = []
    countries = set()
    for authorship in item.get("authorships", []) or []:
        author = authorship.get("author") or {}
        if author.get("display_name"):
            authors.append(author["display_name"])
        for inst in authorship.get("institutions", []) or []:
            if inst.get("display_name"):
                affiliations.append(inst["display_name"])
            if inst.get("country_code"):
                countries.add(inst["country_code"])
    primary = item.get("primary_location") or {}
    source = primary.get("source") or {}
    oa = item.get("open_access") or {}
    return {
        "id": item.get("id", ""),
        "source": "openalex",
        "title": item.get("title", ""),
        "authors": authors,
        "year": item.get("publication_year"),
        "doi": normalize_doi(item.get("doi")),
        "abstract": abstract_from_inverted_index(item.get("abstract_inverted_index")),
        "venue": source.get("display_name", ""),
        "publisher": item.get("host_venue", {}).get("publisher", "") if item.get("host_venue") else "",
        "document_type": item.get("type", ""),
        "language": item.get("language", ""),
        "countries": sorted(countries),
        "affiliations": affiliations,
        "keywords": [kw.get("display_name", "") for kw in item.get("keywords", []) or [] if kw.get("display_name")],
        "concepts": [c.get("display_name", "") for c in item.get("concepts", []) or [] if c.get("display_name")],
        "citation_count": item.get("cited_by_count"),
        "is_open_access": oa.get("is_oa"),
        "license": primary.get("license", "") or oa.get("oa_status", ""),
        "url": item.get("doi") or item.get("id", ""),
        "pdf_url": primary.get("pdf_url") or oa.get("oa_url", "") or "",
        "source_record": item,
    }


def normalize_crossref(item: Dict[str, Any]) -> Dict[str, Any]:
    authors = []
    affiliations = []
    countries = set()
    for author in item.get("author", []) or []:
        name = " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part).strip()
        if name:
            authors.append(name)
        for aff in author.get("affiliation", []) or []:
            if aff.get("name"):
                affiliations.append(aff["name"])
    issued = item.get("issued", {}).get("date-parts", [[None]])
    year = issued[0][0] if issued and issued[0] else None
    links = item.get("link", []) or []
    pdf_url = ""
    for link in links:
        if "pdf" in (link.get("content-type", "") or "").lower() and link.get("URL"):
            pdf_url = link["URL"]
            break
    return {
        "id": item.get("URL", ""),
        "source": "crossref",
        "title": (item.get("title") or [""])[0],
        "authors": authors,
        "year": year,
        "doi": normalize_doi(item.get("DOI")),
        "abstract": item.get("abstract", ""),
        "venue": (item.get("container-title") or [""])[0],
        "publisher": item.get("publisher", ""),
        "document_type": item.get("type", ""),
        "language": item.get("language", ""),
        "countries": sorted(countries),
        "affiliations": affiliations,
        "keywords": item.get("subject", []) or [],
        "concepts": [],
        "citation_count": item.get("is-referenced-by-count"),
        "is_open_access": None,
        "license": ((item.get("license") or [{}])[0]).get("content-version", "") if item.get("license") else "",
        "url": item.get("URL", ""),
        "pdf_url": pdf_url,
        "source_record": item,
    }


def search_openalex(args: argparse.Namespace, countries: List[str]) -> Iterable[Dict[str, Any]]:
    per_page = min(args.max_results, 200)
    filters = []
    if args.from_year:
        filters.append(f"from_publication_date:{args.from_year}-01-01")
    if args.to_year:
        filters.append(f"to_publication_date:{args.to_year}-12-31")
    if countries and len(countries) <= 20:
        filters.append("authorships.institutions.country_code:" + "|".join(countries))
    params = {
        "search": args.query,
        "per-page": str(per_page),
        "sort": "relevance_score:desc",
    }
    if filters:
        params["filter"] = ",".join(filters)
    if args.email:
        params["mailto"] = args.email
    url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
    data = get_json(url, args.user_agent)
    count = 0
    for item in data.get("results", []) or []:
        record = normalize_openalex(item)
        if countries and len(countries) > 20:
            if not set(record["countries"]).intersection(countries):
                continue
        yield record
        count += 1
        if count >= args.max_results:
            break


def search_crossref(args: argparse.Namespace, countries: List[str]) -> Iterable[Dict[str, Any]]:
    params = {
        "query": args.query,
        "rows": str(min(args.max_results, 100)),
        "sort": "relevance",
        "order": "desc",
    }
    filters = []
    if args.from_year:
        filters.append(f"from-pub-date:{args.from_year}-01-01")
    if args.to_year:
        filters.append(f"until-pub-date:{args.to_year}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    if args.email:
        params["mailto"] = args.email
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    data = get_json(url, args.user_agent)
    count = 0
    for item in (data.get("message") or {}).get("items", []) or []:
        record = normalize_crossref(item)
        record["countries_filter_requested"] = countries
        yield record
        count += 1
        if count >= args.max_results:
            break


def dedupe(records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    seen = set()
    for record in records:
        doi = record.get("doi") or ""
        title_key = " ".join((record.get("title") or "").lower().split())
        key = ("doi", doi) if doi else ("title-year", title_key, record.get("year"))
        if key in seen:
            continue
        seen.add(key)
        yield record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--regions", default="")
    parser.add_argument("--from-year", type=int)
    parser.add_argument("--to-year", type=int)
    parser.add_argument("--sources", default="openalex,crossref")
    parser.add_argument("--max-results", type=int, default=50)
    parser.add_argument("--output", required=True)
    parser.add_argument("--email", default="")
    parser.add_argument("--user-agent", default="research-paper-crawler/1.0 (mailto:research@example.local)")
    parser.add_argument("--delay", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    regions = split_regions(args.regions)
    countries = countries_for_regions(regions)
    sources = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
    records: List[Dict[str, Any]] = []
    for source in sources:
        if source == "openalex":
            records.extend(search_openalex(args, countries))
        elif source == "crossref":
            records.extend(search_crossref(args, countries))
        else:
            print(f"unsupported source skipped: {source}", file=sys.stderr)
        time.sleep(args.delay)
    with open(args.output, "w", encoding="utf-8") as fh:
        for record in dedupe(records):
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
