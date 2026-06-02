#!/usr/bin/env python3
"""Retry open-access PDF discovery through Unpaywall and DOAJ."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import socket
import time
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path
from typing import Any, Iterable


USER_AGENT = "research-paper-crawler/1.0 (+oa-source-retry)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--pattern", default="*.filtered.jsonl")
    parser.add_argument("--sources", default="unpaywall,doaj")
    parser.add_argument("--email", default="research-paper-crawler@example.org")
    parser.add_argument("--timeout", type=float, default=12.0)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--max-records", type=int, default=0)
    args = parser.parse_args()
    socket.setdefaulttimeout(args.timeout)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / ".oa_source_cache"
    cache_dir.mkdir(exist_ok=True)

    sources = {source.strip().lower() for source in args.sources.split(",") if source.strip()}
    records = dedupe(list(load_records(input_dir, args.pattern)))
    stats = {
        "records_with_doi": len(records),
        "downloaded": 0,
        "skipped_existing": 0,
        "skipped_no_url": 0,
        "skipped_robots": 0,
        "skipped_researchgate": 0,
        "failed": 0,
    }
    rows: list[dict[str, Any]] = []
    robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    for index, record in enumerate(records, 1):
        if args.max_records and index > args.max_records:
            break

        filename = make_filename(record)
        pdf_path = output_dir / filename
        row = base_row(record, pdf_path)
        if pdf_path.exists() and pdf_path.stat().st_size > 1024:
            stats["skipped_existing"] += 1
            row["status"] = "existing"
            rows.append(row)
            continue

        urls: list[tuple[str, str]] = []
        if "unpaywall" in sources:
            urls.extend(unpaywall_urls(record["doi"], args.email, cache_dir, args.timeout))
        if "doaj" in sources:
            urls.extend(doaj_urls(record["doi"], cache_dir, args.timeout))

        urls = dedupe_urls(urls)
        if not urls:
            stats["skipped_no_url"] += 1
            row["status"] = "skipped_no_url"
            rows.append(row)
            continue

        errors: list[str] = []
        robots_skips = 0
        researchgate_skips = 0
        for source, url in urls:
            if "researchgate.net" in urllib.parse.urlparse(url).netloc.lower():
                researchgate_skips += 1
                errors.append(f"{source}: researchgate public page not downloaded: {url}")
                continue
            if not robots_allowed(url, robots_cache):
                robots_skips += 1
                errors.append(f"{source}: robots disallowed: {url}")
                continue
            try:
                size = download_pdf(url, pdf_path, args.timeout)
                stats["downloaded"] += 1
                row["status"] = "downloaded"
                row["bytes"] = size
                row["pdf_url"] = url
                row["source_used"] = source
                print(f"[{index}/{len(records)}] downloaded {filename} via {source}")
                time.sleep(max(args.delay, 0))
                break
            except Exception as exc:  # noqa: BLE001 - keep batch running.
                errors.append(f"{source}: {url}: {exc}")
                if pdf_path.exists():
                    pdf_path.unlink()
        else:
            row["error"] = " | ".join(errors)
            if researchgate_skips and researchgate_skips == len(urls):
                stats["skipped_researchgate"] += 1
                row["status"] = "skipped_researchgate"
            elif robots_skips and robots_skips + researchgate_skips == len(urls):
                stats["skipped_robots"] += 1
                row["status"] = "skipped_robots"
            else:
                stats["failed"] += 1
                row["status"] = "failed"
            print(f"[{index}/{len(records)}] {row['status']} {filename}: {row['error']}")
        rows.append(row)

    manifest_path = output_dir / "pdf_retry_sources_manifest.csv"
    write_manifest(manifest_path, rows)
    stats_path = output_dir / "pdf_retry_sources_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"manifest: {manifest_path}")
    print(f"stats: {stats_path}")
    return 0


def load_records(input_dir: Path, pattern: str) -> Iterable[dict[str, Any]]:
    for path in sorted(input_dir.rglob(pattern)):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                doi = normalize_doi(str(record.get("doi") or ""))
                if not doi:
                    continue
                record["doi"] = doi
                record["_metadata_file"] = str(path)
                yield record


def normalize_doi(value: str) -> str:
    value = value.strip()
    if value.lower().startswith("https://doi.org/"):
        value = value[16:]
    if value.lower().startswith("http://doi.org/"):
        value = value[15:]
    return value.lower()


def dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in records:
        key = record["doi"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def dedupe_urls(urls: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for source, url in urls:
        if not url.startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)
        unique.append((source, url))
    return unique


def unpaywall_urls(doi: str, email: str, cache_dir: Path, timeout: float) -> list[tuple[str, str]]:
    cache_path = cache_dir / f"unpaywall_{hashlib.sha1(doi.encode()).hexdigest()}.json"
    data = cached_json(cache_path)
    if data is None:
        url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi, safe='')}?email={urllib.parse.quote(email)}"
        data = safe_request_json(url, timeout)
        cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    if not data or data.get("is_oa") is not True:
        return []
    locations = []
    if isinstance(data.get("best_oa_location"), dict):
        locations.append(data["best_oa_location"])
    locations.extend(item for item in data.get("oa_locations", []) if isinstance(item, dict))
    urls: list[tuple[str, str]] = []
    for location in locations:
        for key in ("url_for_pdf", "url"):
            value = location.get(key)
            if isinstance(value, str):
                urls.append(("unpaywall", value))
    return urls


def doaj_urls(doi: str, cache_dir: Path, timeout: float) -> list[tuple[str, str]]:
    cache_path = cache_dir / f"doaj_{hashlib.sha1(doi.encode()).hexdigest()}.json"
    data = cached_json(cache_path)
    if data is None:
        query = urllib.parse.quote(f'doi:"{doi}"')
        data = safe_request_json(f"https://doaj.org/api/search/articles/{query}?pageSize=5", timeout)
        cache_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    urls: list[tuple[str, str]] = []
    for result in data.get("results", []) if isinstance(data, dict) else []:
        bibjson = result.get("bibjson") or {}
        for link in bibjson.get("link", []):
            if not isinstance(link, dict):
                continue
            url = link.get("url")
            content_type = str(link.get("content_type") or "").lower()
            link_type = str(link.get("type") or "").lower()
            if isinstance(url, str) and ("pdf" in content_type or "fulltext" in link_type or url.lower().endswith(".pdf")):
                urls.append(("doaj", url))
    return urls


def cached_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def request_json(url: str, timeout: float) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def safe_request_json(url: str, timeout: float) -> Any:
    try:
        return request_json(url, timeout)
    except Exception as exc:  # noqa: BLE001 - cache miss/HTTP errors should not stop the batch.
        return {"_error": str(exc)}


def robots_allowed(url: str, cache: dict[str, urllib.robotparser.RobotFileParser]) -> bool:
    parsed = urllib.parse.urlparse(url)
    root = f"{parsed.scheme}://{parsed.netloc}"
    if root not in cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(f"{root}/robots.txt")
        try:
            rp.read()
        except Exception:
            return False
        cache[root] = rp
    return cache[root].can_fetch(USER_AGENT, url)


def download_pdf(url: str, path: Path, timeout: float) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "")
        data = response.read()
    if len(data) < 1024:
        raise ValueError("response too small to be a PDF")
    if not data.startswith(b"%PDF") and "pdf" not in content_type.lower():
        raise ValueError(f"response is not a PDF: content-type={content_type!r}")
    path.write_bytes(data)
    return len(data)


def make_filename(record: dict[str, Any]) -> str:
    year = str(record.get("year") or "unknown")
    title = slugify(str(record.get("title") or "paper"))[:90]
    suffix = hashlib.sha1(record["doi"].encode("utf-8")).hexdigest()[:10]
    return f"{year}_{title}_{suffix}.pdf"


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return value or "paper"


def base_row(record: dict[str, Any], pdf_path: Path) -> dict[str, Any]:
    return {
        "status": "pending",
        "file": str(pdf_path),
        "bytes": "",
        "source_used": "",
        "title": record.get("title", ""),
        "year": record.get("year", ""),
        "doi": record.get("doi", ""),
        "pdf_url": "",
        "metadata_file": record.get("_metadata_file", ""),
        "error": "",
    }


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["status", "file", "bytes", "source_used", "title", "year", "doi", "pdf_url", "metadata_file", "error"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
