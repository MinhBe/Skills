#!/usr/bin/env python3
"""Export normalized paper records to CSV, Markdown, BibTeX, RIS, or JSONL."""

from __future__ import annotations

import argparse
import csv
import json
from typing import Any, Dict, List


def load_jsonl(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def compact(value: Any) -> str:
    if isinstance(value, list):
        return "; ".join(str(v) for v in value if v is not None)
    if value is None:
        return ""
    return str(value)


def export_csv(records: List[Dict[str, Any]], output: str) -> None:
    fields = [
        "title", "authors", "year", "doi", "venue", "publisher", "source",
        "countries", "citation_count", "is_open_access", "license", "url",
        "pdf_url",
    ]
    with open(output, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({field: compact(record.get(field)) for field in fields})


def export_md(records: List[Dict[str, Any]], output: str) -> None:
    with open(output, "w", encoding="utf-8") as fh:
        fh.write("# Research Paper Results\n\n")
        fh.write(f"Total records: {len(records)}\n\n")
        for idx, record in enumerate(records, 1):
            fh.write(f"## {idx}. {record.get('title', '')}\n\n")
            fh.write(f"- Authors: {compact(record.get('authors'))}\n")
            fh.write(f"- Year: {compact(record.get('year'))}\n")
            fh.write(f"- DOI: {compact(record.get('doi'))}\n")
            fh.write(f"- Venue: {compact(record.get('venue'))}\n")
            fh.write(f"- Countries: {compact(record.get('countries'))}\n")
            fh.write(f"- Source: {compact(record.get('source'))}\n")
            fh.write(f"- URL: {compact(record.get('url'))}\n")
            if record.get("pdf_url"):
                fh.write(f"- PDF: {compact(record.get('pdf_url'))}\n")
            abstract = compact(record.get("abstract"))
            if abstract:
                fh.write(f"\n{abstract}\n")
            fh.write("\n")


def bib_key(record: Dict[str, Any], index: int) -> str:
    first_author = "paper"
    authors = record.get("authors") or []
    if authors:
        first_author = "".join(ch for ch in authors[0].split()[-1].lower() if ch.isalnum())
    return f"{first_author}{record.get('year') or 'nd'}_{index}"


def export_bib(records: List[Dict[str, Any]], output: str) -> None:
    with open(output, "w", encoding="utf-8") as fh:
        for idx, record in enumerate(records, 1):
            fh.write(f"@article{{{bib_key(record, idx)},\n")
            fh.write(f"  title = {{{record.get('title', '')}}},\n")
            fh.write(f"  author = {{{' and '.join(record.get('authors') or [])}}},\n")
            if record.get("year"):
                fh.write(f"  year = {{{record.get('year')}}},\n")
            if record.get("venue"):
                fh.write(f"  journal = {{{record.get('venue')}}},\n")
            if record.get("doi"):
                fh.write(f"  doi = {{{record.get('doi')}}},\n")
            if record.get("url"):
                fh.write(f"  url = {{{record.get('url')}}},\n")
            fh.write("}\n\n")


def export_ris(records: List[Dict[str, Any]], output: str) -> None:
    with open(output, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write("TY  - JOUR\n")
            fh.write(f"TI  - {record.get('title', '')}\n")
            for author in record.get("authors") or []:
                fh.write(f"AU  - {author}\n")
            if record.get("year"):
                fh.write(f"PY  - {record.get('year')}\n")
            if record.get("venue"):
                fh.write(f"JO  - {record.get('venue')}\n")
            if record.get("doi"):
                fh.write(f"DO  - {record.get('doi')}\n")
            if record.get("url"):
                fh.write(f"UR  - {record.get('url')}\n")
            fh.write("ER  - \n\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--format", choices=["jsonl", "csv", "md", "bibtex", "ris"], required=True)
    args = parser.parse_args()
    records = load_jsonl(args.input)
    if args.format == "jsonl":
        with open(args.output, "w", encoding="utf-8") as fh:
            for record in records:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    elif args.format == "csv":
        export_csv(records, args.output)
    elif args.format == "md":
        export_md(records, args.output)
    elif args.format == "bibtex":
        export_bib(records, args.output)
    elif args.format == "ris":
        export_ris(records, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
