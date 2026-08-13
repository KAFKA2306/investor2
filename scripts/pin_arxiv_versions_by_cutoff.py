#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from pin_arxiv_versions import (
    ROOT,
    canonical_json_bytes,
    fetch_specific_versions,
    sha256_file,
    selected_candidates,
)

SCHEMA_VERSION = "investor2.arxiv-version-pins-by-cutoff.v1"
EXPLICIT_VERSION = re.compile(r"https://arxiv\.org/abs/(?P<id>\d{4}\.\d{4,5})v(?P<n>[1-9]\d*)$")
EXPECTED_2019_SOURCE_SHA256 = "7d7fcb2639219c5a2e528ac63347e2d18b73fa46ed8637e4832322dd9c8b90cb"


def explicit_latest(candidate: dict[str, Any]) -> tuple[str, int]:
    arxiv_id = str(candidate.get("arxiv_id", ""))
    url = str(candidate.get("abs_url", ""))
    match = EXPLICIT_VERSION.fullmatch(url)
    if not match or match.group("id") != arxiv_id:
        raise ValueError(f"{arxiv_id}: selection abs_url must pin the current explicit arXiv version")
    return arxiv_id, int(match.group("n"))


def query_ids_for_candidate(candidate: dict[str, Any]) -> list[str]:
    arxiv_id, latest_n = explicit_latest(candidate)
    return [f"{arxiv_id}v{n}" for n in range(1, latest_n + 1)]


def build_pin(
    candidate: dict[str, Any],
    entries: dict[str, dict[str, str]],
    *,
    cutoff: str,
    inspected_at: str,
) -> dict[str, Any]:
    arxiv_id, latest_n = explicit_latest(candidate)
    versions: list[dict[str, Any]] = []
    missing: list[str] = []
    for n in range(1, latest_n + 1):
        query_id = f"{arxiv_id}v{n}"
        entry = entries.get(query_id)
        if entry is None:
            missing.append(query_id)
            continue
        versions.append(
            {
                "version": f"v{n}",
                "query_id": query_id,
                "published": entry.get("published") or None,
                "updated": entry.get("updated") or None,
                "url": f"https://arxiv.org/abs/{query_id}",
            }
        )

    eligible = [
        row for row in versions
        if isinstance(row.get("updated"), str) and row["updated"] <= cutoff
    ]
    selected = eligible[-1] if eligible else None
    status = "VERIFIED"
    reasons: list[str] = []
    if missing:
        status = "CONFLICT"
        reasons.append("MISSING_EXPLICIT_VERSION_FROM_PRIMARY_API")
    if selected is None:
        status = "UNKNOWN" if status == "VERIFIED" else status
        reasons.append("NO_VERSION_PUBLIC_BY_CUTOFF")

    first = next((row for row in versions if row["version"] == "v1"), None)
    later = [] if selected is None else [
        row["version"] for row in versions
        if int(row["version"][1:]) > int(selected["version"][1:])
    ]
    return {
        "arxiv_id": arxiv_id,
        "title": candidate.get("title"),
        "availability_status": status,
        "cutoff": cutoff,
        "selected_version": selected["version"] if selected else None,
        "selected_version_url": selected["url"] if selected else None,
        "version_submitted_at": selected["updated"] if selected else None,
        "first_submitted_at": first["published"] if first else None,
        "current_latest_version": f"v{latest_n}",
        "selection_snapshot_abs_url": candidate.get("abs_url"),
        "later_revisions_excluded": later,
        "inspected_at": inspected_at,
        "reasons": reasons,
        "versions": versions,
    }


def build_manifest(
    selection: dict[str, Any],
    *,
    selection_sha256: str,
    entries: dict[str, dict[str, str]],
    provenance: list[dict[str, Any]],
    cutoff: str,
    inspected_at: str,
) -> dict[str, Any]:
    source = selection.get("source_snapshot")
    if not isinstance(source, dict):
        raise ValueError("selection source_snapshot is required")
    if source.get("artifact_sha256") != EXPECTED_2019_SOURCE_SHA256:
        raise ValueError("unexpected 2019 source snapshot SHA-256")
    selected = selected_candidates(selection)
    pins = [build_pin(row, entries, cutoff=cutoff, inspected_at=inspected_at) for row in selected]
    statuses = [row["availability_status"] for row in pins]
    return {
        "schema_version": SCHEMA_VERSION,
        "population_year": 2019,
        "cutoff": cutoff,
        "policy": "Select the highest explicit arXiv version whose primary-API updated timestamp is at or before the cutoff; never substitute the current latest revision after cutoff.",
        "selection_manifest_sha256": selection_sha256,
        "source_snapshot_sha256": source["artifact_sha256"],
        "inspected_at": inspected_at,
        "summary": {
            "selected_count": len(pins),
            "status_counts": {status: statuses.count(status) for status in ("VERIFIED", "UNKNOWN", "CONFLICT")},
        },
        "request_provenance": provenance,
        "pins": pins,
    }


def validate(manifest: dict[str, Any], *, require_all_verified: bool = True) -> None:
    pins = manifest.get("pins")
    if not isinstance(pins, list):
        raise ValueError("pins are required")
    if manifest.get("summary", {}).get("selected_count") != len(pins):
        raise ValueError("selected_count mismatch")
    ids = [row.get("arxiv_id") for row in pins]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate arXiv ids")
    if require_all_verified:
        bad = [row["arxiv_id"] for row in pins if row["availability_status"] != "VERIFIED"]
        if bad:
            raise ValueError("unverified version pins: " + ", ".join(bad))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cutoff", default="2019-12-31T23:59:59Z")
    parser.add_argument("--inspected-at", required=True)
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--pause-seconds", type=float, default=3.0)
    parser.add_argument("--allow-unverified", action="store_true")
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    selected = selected_candidates(selection)
    query_ids = [query_id for row in selected for query_id in query_ids_for_candidate(row)]
    entries, provenance = fetch_specific_versions(
        query_ids, batch_size=args.batch_size, pause_seconds=args.pause_seconds
    )
    manifest = build_manifest(
        selection,
        selection_sha256=sha256_file(args.selection),
        entries=entries,
        provenance=provenance,
        cutoff=args.cutoff,
        inspected_at=args.inspected_at,
    )
    validate(manifest, require_all_verified=not args.allow_unverified)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(manifest))
    print(json.dumps(manifest["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
