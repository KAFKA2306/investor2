#!/usr/bin/env python3
"""Pin explicit arXiv versions and public-availability timestamps for Stage B.

The Stage A selector is intentionally ex-post: it was built from a 2026 metadata
snapshot. This module does not rewrite that history. Instead, for every SELECT
candidate it takes the explicit version already present in the selection
manifest (for example ``2105.11376v2``), queries that *specific* arXiv version,
and records when the first submission and selected version became public.

Unknown or conflicting evidence is never guessed into VERIFIED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTION = ROOT / "docs/research/catalogs/arxiv_qfin_2021_selection_manifest.json"
SCHEMA_VERSION = "investor2.arxiv-version-pins.v1"
EXPECTED_SOURCE_SNAPSHOT_SHA256 = (
    "a1ebbbd25ae65b5bce391ccb8ded1a27fa7c013102581251cc1f6ee4e73a948c"
)
ARXIV_EXPLICIT_VERSION = re.compile(
    r"https://arxiv\.org/abs/(?P<id>\d{4}\.\d{4,5})v(?P<version>[1-9]\d*)$"
)
ATOM = "{http://www.w3.org/2005/Atom}"
API_BASE = "https://export.arxiv.org/api/query"
USER_AGENT = "KAFKA2306-investor2-version-audit/1.0 (+https://github.com/KAFKA2306/investor2)"


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def selected_candidates(selection: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = selection.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("selection manifest candidates are required")
    return [row for row in candidates if row.get("decision") == "SELECT"]


def explicit_query_id(candidate: dict[str, Any]) -> tuple[str, str]:
    arxiv_id = str(candidate.get("arxiv_id", ""))
    abs_url = str(candidate.get("abs_url", ""))
    match = ARXIV_EXPLICIT_VERSION.fullmatch(abs_url)
    if not match:
        raise ValueError(f"{arxiv_id}: SELECT abs_url must pin an explicit arXiv version")
    if match.group("id") != arxiv_id:
        raise ValueError(f"{arxiv_id}: abs_url arXiv id mismatch")
    version = f"v{match.group('version')}"
    return f"{arxiv_id}{version}", version


def _entry_query_id(entry: ET.Element) -> str:
    identifier = (entry.findtext(f"{ATOM}id") or "").strip().rstrip("/")
    return identifier.rsplit("/", 1)[-1]


def parse_atom_entries(payload: bytes) -> dict[str, dict[str, str]]:
    root = ET.fromstring(payload)
    output: dict[str, dict[str, str]] = {}
    for entry in root.findall(f"{ATOM}entry"):
        query_id = _entry_query_id(entry)
        if not query_id:
            continue
        output[query_id] = {
            "query_id": query_id,
            "published": (entry.findtext(f"{ATOM}published") or "").strip(),
            "updated": (entry.findtext(f"{ATOM}updated") or "").strip(),
            "title": " ".join((entry.findtext(f"{ATOM}title") or "").split()),
        }
    return output


def _request_url(query_ids: list[str]) -> str:
    query = urllib.parse.urlencode(
        {"id_list": ",".join(query_ids), "start": 0, "max_results": len(query_ids)}
    )
    return f"{API_BASE}?{query}"


def fetch_specific_versions(
    query_ids: list[str], *, batch_size: int = 40, pause_seconds: float = 3.0
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    entries: dict[str, dict[str, str]] = {}
    provenance: list[dict[str, Any]] = []
    for start in range(0, len(query_ids), batch_size):
        batch = query_ids[start : start + batch_size]
        url = _request_url(batch)
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = response.read()
        parsed = parse_atom_entries(payload)
        entries.update(parsed)
        provenance.append(
            {
                "query_ids": batch,
                "request_url": url,
                "response_sha256": sha256_bytes(payload),
                "entry_count": len(parsed),
            }
        )
        if start + batch_size < len(query_ids) and pause_seconds:
            time.sleep(pause_seconds)
    return entries, provenance


def _iso_looks_valid(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value))


def build_pin_record(
    candidate: dict[str, Any],
    entry: dict[str, str] | None,
    *,
    inspected_at: str,
    source_snapshot_sha256: str,
) -> dict[str, Any]:
    arxiv_id = str(candidate.get("arxiv_id", ""))
    base: dict[str, Any] = {
        "arxiv_id": arxiv_id,
        "selected_version": None,
        "selected_version_url": None,
        "version_submitted_at": None,
        "first_submitted_at": None,
        "inspected_source_url": None,
        "inspected_at": inspected_at,
        "availability_status": "UNKNOWN",
        "available_by_2021_end": None,
        "provenance": {
            "selection_source_snapshot_sha256": source_snapshot_sha256,
            "selection_abs_url": candidate.get("abs_url"),
            "selection_published": candidate.get("published"),
            "selection_updated": candidate.get("updated"),
        },
        "evidence": [],
    }
    try:
        query_id, version = explicit_query_id(candidate)
    except ValueError as error:
        base["availability_status"] = "CONFLICT"
        base["evidence"] = [{"kind": "selection_version_conflict", "detail": str(error)}]
        return base

    version_url = f"https://arxiv.org/abs/{query_id}"
    api_url = f"{API_BASE}?" + urllib.parse.urlencode({"id_list": query_id})
    base.update(
        {
            "selected_version": version,
            "selected_version_url": version_url,
            "inspected_source_url": api_url,
        }
    )
    base["evidence"].append(
        {
            "kind": "selection_explicit_version",
            "url": candidate["abs_url"],
            "query_id": query_id,
        }
    )
    if entry is None:
        base["evidence"].append(
            {
                "kind": "arxiv_specific_version_missing",
                "url": api_url,
                "query_id": query_id,
            }
        )
        return base

    published = entry.get("published", "")
    updated = entry.get("updated", "")
    conflicts: list[str] = []
    if entry.get("query_id") != query_id:
        conflicts.append(f"returned id {entry.get('query_id')!r} != requested {query_id!r}")
    if not _iso_looks_valid(published) or not _iso_looks_valid(updated):
        conflicts.append("arXiv published/updated timestamp is missing or malformed")
    if published and candidate.get("published") != published:
        conflicts.append(
            f"selection published {candidate.get('published')!r} != arXiv {published!r}"
        )
    if updated and candidate.get("updated") != updated:
        conflicts.append(
            f"selection updated {candidate.get('updated')!r} != selected-version arXiv {updated!r}"
        )

    base["first_submitted_at"] = published or None
    base["version_submitted_at"] = updated or None
    base["available_by_2021_end"] = (
        updated <= "2021-12-31T23:59:59Z" if _iso_looks_valid(updated) else None
    )
    base["evidence"].append(
        {
            "kind": "arxiv_atom_specific_version",
            "url": api_url,
            "query_id": query_id,
            "published": published or None,
            "updated": updated or None,
        }
    )
    if conflicts:
        base["availability_status"] = "CONFLICT"
        base["evidence"].append(
            {"kind": "timestamp_or_version_conflict", "detail": "; ".join(conflicts)}
        )
    else:
        base["availability_status"] = "VERIFIED"
    return base


def build_manifest(
    selection: dict[str, Any],
    *,
    selection_manifest_sha256: str,
    entries: dict[str, dict[str, str]],
    request_provenance: list[dict[str, Any]],
    inspected_at: str,
) -> dict[str, Any]:
    if not _iso_looks_valid(inspected_at):
        raise ValueError("inspected_at must be UTC ISO-8601 seconds, e.g. 2026-08-13T09:00:00Z")
    source = selection.get("source_snapshot")
    if not isinstance(source, dict):
        raise ValueError("selection manifest source_snapshot is required")
    source_sha = str(source.get("artifact_sha256", ""))
    if source_sha != EXPECTED_SOURCE_SNAPSHOT_SHA256:
        raise ValueError(f"unexpected source snapshot SHA-256: {source_sha}")

    selected = selected_candidates(selection)
    pins: list[dict[str, Any]] = []
    for candidate in selected:
        try:
            query_id, _ = explicit_query_id(candidate)
        except ValueError:
            query_id = ""
        pins.append(
            build_pin_record(
                candidate,
                entries.get(query_id) if query_id else None,
                inspected_at=inspected_at,
                source_snapshot_sha256=source_sha,
            )
        )

    status_counts = {
        status: sum(pin["availability_status"] == status for pin in pins)
        for status in ("VERIFIED", "UNKNOWN", "CONFLICT")
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "selection_manifest_sha256": selection_manifest_sha256,
        "source_snapshot_sha256": source_sha,
        "selection_time_basis": "EX_POST_2026_METADATA_NOT_2021_VINTAGE",
        "version_policy": (
            "Pin the explicit arXiv version already selected by Stage A; query that exact vN "
            "through the arXiv Atom API and preserve its first-submission and selected-version timestamps."
        ),
        "inspected_at": inspected_at,
        "summary": {
            "selected_count": len(selected),
            "status_counts": status_counts,
            "post_2021_selected_versions": sum(
                pin["availability_status"] == "VERIFIED"
                and pin["available_by_2021_end"] is False
                for pin in pins
            ),
        },
        "request_provenance": request_provenance,
        "pins": pins,
    }


def validate_pin_manifest(manifest: dict[str, Any], *, require_all_verified: bool) -> None:
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported version pin schema")
    pins = manifest.get("pins")
    summary = manifest.get("summary")
    if not isinstance(pins, list) or not isinstance(summary, dict):
        raise ValueError("version pins and summary are required")
    ids = [pin.get("arxiv_id") for pin in pins]
    if any(not isinstance(item, str) or not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("arXiv pin ids must be unique non-empty strings")
    statuses = [pin.get("availability_status") for pin in pins]
    if any(status not in {"VERIFIED", "UNKNOWN", "CONFLICT"} for status in statuses):
        raise ValueError("unknown availability status")
    if summary.get("selected_count") != len(pins):
        raise ValueError("selected_count does not match pins")
    expected_counts = {status: statuses.count(status) for status in ("VERIFIED", "UNKNOWN", "CONFLICT")}
    if summary.get("status_counts") != expected_counts:
        raise ValueError("status_counts do not match pins")
    for pin in pins:
        if pin["availability_status"] == "VERIFIED":
            for key in (
                "selected_version",
                "selected_version_url",
                "version_submitted_at",
                "first_submitted_at",
                "inspected_source_url",
                "inspected_at",
            ):
                if not pin.get(key):
                    raise ValueError(f"VERIFIED pin {pin['arxiv_id']} missing {key}")
    if require_all_verified and any(status != "VERIFIED" for status in statuses):
        bad = [
            pin["arxiv_id"]
            for pin in pins
            if pin["availability_status"] != "VERIFIED"
        ]
        raise ValueError("Stage B blocked by unverified version pins: " + ", ".join(bad))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", type=Path, default=DEFAULT_SELECTION)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--inspected-at", required=True)
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--pause-seconds", type=float, default=3.0)
    parser.add_argument("--allow-unverified", action="store_true")
    args = parser.parse_args()

    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    selected = selected_candidates(selection)
    query_ids = [explicit_query_id(candidate)[0] for candidate in selected]
    entries, provenance = fetch_specific_versions(
        query_ids, batch_size=args.batch_size, pause_seconds=args.pause_seconds
    )
    manifest = build_manifest(
        selection,
        selection_manifest_sha256=sha256_file(args.selection),
        entries=entries,
        request_provenance=provenance,
        inspected_at=args.inspected_at,
    )
    validate_pin_manifest(manifest, require_all_verified=not args.allow_unverified)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(manifest))
    print(json.dumps(manifest["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
