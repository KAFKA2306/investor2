#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from snapshot_store import ROOT, append_entry, build_entry, load_registry

API_URL = "https://export.arxiv.org/api/query"
API_DOC_URL = "https://info.arxiv.org/help/api/user-manual.html"
API_TERMS_URL = "https://info.arxiv.org/help/api/tou.html"
TAXONOMY_URL = "https://arxiv.org/category_taxonomy"
SCHEMA_VERSION = "investor2.arxiv-qfin-metadata.v1"
SOURCE_ID = "arxiv_api_metadata"
QFIN_CATEGORIES = (
    "q-fin.CP",
    "q-fin.GN",
    "q-fin.MF",
    "q-fin.PM",
    "q-fin.PR",
    "q-fin.RM",
    "q-fin.ST",
    "q-fin.TR",
)
ATOM = "http://www.w3.org/2005/Atom"
OPENSEARCH = "http://a9.com/-/spec/opensearch/1.1/"
ARXIV = "http://arxiv.org/schemas/atom"
VERSION_SUFFIX = re.compile(r"v\d+$")


def normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split())
    return normalized or None


def build_search_query(year: int) -> str:
    categories = " OR ".join(f"cat:{category}" for category in QFIN_CATEGORIES)
    return (
        f"({categories}) AND "
        f"submittedDate:[{year:04d}01010000 TO {year:04d}12312359]"
    )


def build_query_url(*, search_query: str, start: int, max_results: int) -> str:
    params = {
        "search_query": search_query,
        "start": str(start),
        "max_results": str(max_results),
        "sortBy": "submittedDate",
        "sortOrder": "ascending",
    }
    return f"{API_URL}?{urllib.parse.urlencode(params)}"


def _child_text(entry: ET.Element, namespace: str, tag: str) -> str | None:
    child = entry.find(f"{{{namespace}}}{tag}")
    return normalize_text(child.text if child is not None else None)


def parse_feed(xml_bytes: bytes) -> tuple[int, list[dict[str, Any]]]:
    root = ET.fromstring(xml_bytes)
    total_node = root.find(f"{{{OPENSEARCH}}}totalResults")
    if total_node is None or total_node.text is None:
        raise AssertionError("arXiv response missing opensearch:totalResults")
    total_results = int(total_node.text.strip())

    records: list[dict[str, Any]] = []
    for entry in root.findall(f"{{{ATOM}}}entry"):
        raw_id = _child_text(entry, ATOM, "id")
        if not raw_id:
            raise AssertionError("arXiv entry missing id")
        versioned_id = raw_id.rsplit("/", 1)[-1]
        arxiv_id = VERSION_SUFFIX.sub("", versioned_id)

        links: dict[str, str] = {}
        for link in entry.findall(f"{{{ATOM}}}link"):
            href = link.attrib.get("href")
            rel = link.attrib.get("rel", "")
            link_type = link.attrib.get("type", "")
            if not href:
                continue
            if rel == "alternate":
                links["abs"] = href.replace("http://", "https://", 1)
            if link_type == "application/pdf":
                links["pdf"] = href.replace("http://", "https://", 1)

        authors = [
            name
            for author in entry.findall(f"{{{ATOM}}}author")
            if (name := _child_text(author, ATOM, "name"))
        ]
        categories = sorted(
            {
                category.attrib["term"]
                for category in entry.findall(f"{{{ATOM}}}category")
                if category.attrib.get("term")
            }
        )
        primary_node = entry.find(f"{{{ARXIV}}}primary_category")
        primary_category = (
            primary_node.attrib.get("term") if primary_node is not None else None
        )

        records.append(
            {
                "arxiv_id": arxiv_id,
                "versioned_id": versioned_id,
                "title": _child_text(entry, ATOM, "title"),
                "authors": authors,
                "abstract": _child_text(entry, ATOM, "summary"),
                "published": _child_text(entry, ATOM, "published"),
                "updated": _child_text(entry, ATOM, "updated"),
                "primary_category": primary_category,
                "categories": categories,
                "doi": _child_text(entry, ARXIV, "doi"),
                "journal_ref": _child_text(entry, ARXIV, "journal_ref"),
                "comment": _child_text(entry, ARXIV, "comment"),
                "abs_url": links.get("abs", f"https://arxiv.org/abs/{arxiv_id}"),
                "pdf_url": links.get("pdf"),
            }
        )

    return total_results, records


def fetch_page(url: str, *, timeout_seconds: int = 60) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "KAFKA2306-investor2/1.0 "
                "(https://github.com/KAFKA2306/investor2; arXiv metadata cache)"
            )
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        if response.status != 200:
            raise RuntimeError(f"arXiv API returned HTTP {response.status}")
        return response.read()


def fetch_year(
    year: int,
    *,
    page_size: int = 1000,
    delay_seconds: float = 3.1,
) -> dict[str, Any]:
    if page_size < 1 or page_size > 2000:
        raise ValueError("page_size must be between 1 and 2000")
    search_query = build_search_query(year)
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )

    records_by_id: dict[str, dict[str, Any]] = {}
    start = 0
    total_results: int | None = None
    query_urls: list[str] = []

    while total_results is None or start < total_results:
        query_url = build_query_url(
            search_query=search_query, start=start, max_results=page_size
        )
        query_urls.append(query_url)
        if start:
            time.sleep(delay_seconds)
        page_total, page_records = parse_feed(fetch_page(query_url))
        if total_results is None:
            total_results = page_total
        elif page_total != total_results:
            raise AssertionError(
                f"arXiv totalResults changed during pagination: "
                f"{total_results} -> {page_total}"
            )

        for record in page_records:
            records_by_id[record["arxiv_id"]] = record

        if not page_records:
            break
        start += len(page_records)

    records = sorted(records_by_id.values(), key=lambda item: item["arxiv_id"])
    if total_results is None:
        total_results = 0
    if len(records) != total_results:
        raise AssertionError(
            f"deduplicated record count {len(records)} != arXiv totalResults {total_results}"
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "year": year,
        "retrieved_at": retrieved_at,
        "scope": {
            "archive": "Quantitative Finance",
            "categories": list(QFIN_CATEGORIES),
            "submitted_date_start": f"{year:04d}-01-01T00:00:00Z",
            "submitted_date_end": f"{year:04d}-12-31T23:59:00Z",
            "selection_note": (
                "Complete arXiv metadata population for the eight q-fin categories "
                "excluding q-fin.EC because arXiv defines it as an alias for econ.GN. "
                "This snapshot is a discovery universe, not a claim that every record "
                "is a major or investable finance paper."
            ),
        },
        "source": {
            "api_endpoint": API_URL,
            "search_query": search_query,
            "query_urls": query_urls,
            "api_documentation": API_DOC_URL,
            "api_terms": API_TERMS_URL,
            "category_taxonomy": TAXONOMY_URL,
        },
        "record_count": len(records),
        "records": records,
    }


def write_snapshot(snapshot: dict[str, Any], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def register_snapshot(snapshot: dict[str, Any], output: Path) -> dict[str, Any]:
    relative_path = output.resolve().relative_to(ROOT.resolve()).as_posix()
    provenance = {
        "endpoint": API_URL,
        "query_or_scope": snapshot["source"]["search_query"],
        "retrieved_at": snapshot["retrieved_at"],
        "source_urls": [API_DOC_URL, API_TERMS_URL, TAXONOMY_URL],
    }
    entry = build_entry(
        root=ROOT,
        registry=load_registry(),
        dataset_id=f"arxiv_qfin_{snapshot['year']}_metadata",
        reuse_key=f"arxiv/q-fin/{snapshot['year']}/metadata",
        artifact_path=relative_path,
        source=SOURCE_ID,
        source_kind="api",
        observed_at=snapshot["retrieved_at"],
        schema_version=SCHEMA_VERSION,
        provenance=provenance,
    )
    append_entry(entry)
    return entry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch and optionally register a canonical arXiv q-fin metadata snapshot."
    )
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--page-size", type=int, default=1000)
    parser.add_argument("--delay-seconds", type=float, default=3.1)
    parser.add_argument("--register", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    snapshot = fetch_year(
        args.year,
        page_size=args.page_size,
        delay_seconds=args.delay_seconds,
    )
    write_snapshot(snapshot, output)
    result: dict[str, Any] = {
        "artifact_path": output.resolve().relative_to(ROOT.resolve()).as_posix(),
        "record_count": snapshot["record_count"],
        "retrieved_at": snapshot["retrieved_at"],
    }
    if args.register:
        result["snapshot"] = register_snapshot(snapshot, output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
