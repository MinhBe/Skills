#!/usr/bin/env python3
"""Download open-access PDFs from normalized research metadata JSONL files."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from pathlib import Path
from typing import Any, Iterable


USER_AGENT = "research-paper-crawler/1.0 (+metadata-driven open-access PDF fetch)"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True, help="Directory containing JSONL metadata files.")
    parser.add_argument("--output-dir", required=True, help="Directory where PDFs and manifest are written.")
    parser.add_argument("--pattern", default="*.filtered.jsonl", help="Glob pattern under input-dir.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between downloads in seconds.")
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--max-pdfs", type=int, default=0, help="Optional cap; 0 means no cap.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    socket.setdefaulttimeout(args.timeout)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / "pdf_download_manifest.csv"
    records = list(load_candidates(input_dir, args.pattern))
    unique = dedupe(records)

    stats = {
        "metadata_records": len(records),
        "unique_open_pdf_candidates": len(unique),
        "downloaded": 0,
        "skipped_existing": 0,
        "skipped_robots": 0,
        "failed": 0,
    }

    robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
    rows: list[dict[str, Any]] = []
    processed = 0
    for index, record in enumerate(unique, 1):
        if args.max_pdfs and processed >= args.max_pdfs:
            break
        processed += 1
        urls = record["pdf_urls"]
        filename = make_filename(record)
        pdf_path = output_dir / filename
        row = {
            "status": "pending",
            "file": str(pdf_path),
            "title": record.get("title", ""),
            "year": record.get("year", ""),
            "doi": record.get("doi", ""),
            "source": record.get("source", ""),
            "license": record.get("license", ""),
            "pdf_url": "; ".join(urls),
            "metadata_file": record.get("_metadata_file", ""),
            "error": "",
        }

        if pdf_path.exists() and pdf_path.stat().st_size > 1024:
            stats["skipped_existing"] += 1
            row["status"] = "existing"
            rows.append(row)
            continue

        if args.dry_run:
            row["status"] = "dry_run"
            rows.append(row)
            continue

        errors: list[str] = []
        skipped_by_robots = 0
        for url in urls:
            if not robots_allowed(url, robots_cache):
                skipped_by_robots += 1
                errors.append(f"robots disallowed: {url}")
                continue
            try:
                size = download_pdf(url, pdf_path, args.timeout)
                stats["downloaded"] += 1
                row["status"] = "downloaded"
                row["bytes"] = size
                row["pdf_url"] = url
                print(f"[{index}/{len(unique)}] downloaded {filename}")
                time.sleep(max(args.delay, 0))
                break
            except Exception as exc:  # noqa: BLE001 - keep batch running and log failures.
                errors.append(f"{url}: {exc}")
                if pdf_path.exists():
                    pdf_path.unlink()
        else:
            if skipped_by_robots == len(urls):
                stats["skipped_robots"] += 1
                row["status"] = "skipped_robots"
            else:
                stats["failed"] += 1
                row["status"] = "failed"
            row["error"] = " | ".join(errors)
            print(f"[{index}/{len(unique)}] {row['status']} {filename}: {row['error']}")
        rows.append(row)

    write_manifest(manifest_path, rows)
    stats_path = output_dir / "pdf_download_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"manifest: {manifest_path}")
    print(f"stats: {stats_path}")
    return 0


def load_candidates(input_dir: Path, pattern: str) -> Iterable[dict[str, Any]]:
    for path in sorted(input_dir.rglob(pattern)):
        with path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not is_open(record):
                    continue
                pdf_urls = extract_pdf_urls(record)
                if not pdf_urls:
                    continue
                record["pdf_urls"] = pdf_urls
                record["pdf_url"] = pdf_urls[0]
                record["_metadata_file"] = str(path)
                record["_line_no"] = line_no
                yield record


def is_open(record: dict[str, Any]) -> bool:
    license_text = str(record.get("license") or "").lower()
    if license_text == "closed":
        return False
    if record.get("is_open_access") is True:
        return True
    source_record = record.get("source_record") or {}
    open_access = source_record.get("open_access") or {}
    return open_access.get("is_oa") is True


def extract_pdf_urls(record: dict[str, Any]) -> list[str]:
    urls = [
        ((record.get("source_record") or {}).get("content_urls") or {}).get("pdf"),
        record.get("pdf_url"),
        ((record.get("source_record") or {}).get("open_access") or {}).get("oa_url"),
    ]
    best = (record.get("source_record") or {}).get("best_oa_location") or {}
    urls.append(best.get("pdf_url"))
    found: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
        if url in seen:
            continue
        seen.add(url)
        found.append(url)
    return found


def dedupe(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for record in records:
        key = str(record.get("doi") or record.get("id") or record["pdf_url"]).lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def make_filename(record: dict[str, Any]) -> str:
    year = str(record.get("year") or "unknown")
    title = slugify(str(record.get("title") or "paper"))[:90]
    doi = str(record.get("doi") or record.get("id") or record["pdf_url"])
    suffix = hashlib.sha1(doi.encode("utf-8")).hexdigest()[:10]
    return f"{year}_{title}_{suffix}.pdf"


def slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return value or "paper"


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


def write_manifest(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "status",
        "file",
        "bytes",
        "title",
        "year",
        "doi",
        "source",
        "license",
        "pdf_url",
        "metadata_file",
        "error",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
