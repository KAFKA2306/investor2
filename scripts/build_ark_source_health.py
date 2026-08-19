#!/usr/bin/env python3
"""Verify canonical ARK Big Ideas domain outputs without creating a second data authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data" / "ark-big-ideas" / "source-catalog.json"
DEFAULT_OUTPUT = ROOT / "api" / "v1" / "ark-big-ideas" / "source-health.json"
ALLOWED_STATUSES = {"ready", "accumulating", "blocked_external_evidence", "deferred_by_user"}
UA = "investor2-ark-source-health/1.0 github.com/KAFKA2306/investor2"


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def validate_catalog(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    sources = catalog.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("catalog sources must be a non-empty list")
    logical_ids: set[str] = set()
    current_repos: set[str] = set()
    required = {"theme", "logical_repo", "current_repo", "status", "check_live", "canonical_url", "raw_url", "issue_url"}
    for source in sources:
        missing = required - source.keys()
        if missing:
            raise ValueError(f"source missing fields {sorted(missing)}: {source}")
        logical_id = str(source["logical_repo"])
        current_repo = str(source["current_repo"])
        if logical_id in logical_ids:
            raise ValueError(f"duplicate logical repo: {logical_id}")
        if current_repo in current_repos:
            raise ValueError(f"duplicate current repo: {current_repo}")
        logical_ids.add(logical_id)
        current_repos.add(current_repo)
        if source["status"] not in ALLOWED_STATUSES:
            raise ValueError(f"unknown status {source['status']!r}")
        if source["check_live"] and not source["raw_url"]:
            raise ValueError(f"live source requires raw_url: {logical_id}")
        if source["status"] == "ready" and not source["check_live"]:
            raise ValueError(f"ready source must be live checked: {logical_id}")
        if not str(source["canonical_url"]).startswith("https://github.com/KAFKA2306/"):
            raise ValueError(f"canonical source must stay in KAFKA2306 GitHub: {logical_id}")
    return sources


def fetch_json(url: str) -> tuple[bytes, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    if not raw:
        raise ValueError(f"empty canonical source: {url}")
    return raw, json.loads(raw)


def source_shape(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return {"json_type": "object", "top_level_keys": sorted(payload.keys())}
    if isinstance(payload, list):
        return {"json_type": "array", "item_count": len(payload)}
    raise ValueError(f"canonical JSON must be object or array, got {type(payload).__name__}")


def build_health(catalog: dict[str, Any]) -> dict[str, Any]:
    sources = validate_catalog(catalog)
    checked: list[dict[str, Any]] = []
    status_counts = {status: 0 for status in sorted(ALLOWED_STATUSES)}
    for source in sources:
        status_counts[source["status"]] += 1
        record = {
            "theme": source["theme"],
            "logical_repo": source["logical_repo"],
            "current_repo": source["current_repo"],
            "status": source["status"],
            "canonical_url": source["canonical_url"],
            "issue_url": source["issue_url"],
        }
        if source["check_live"]:
            raw, payload = fetch_json(source["raw_url"])
            record.update(
                {
                    "live_check": "ok",
                    "raw_url": source["raw_url"],
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    **source_shape(payload),
                }
            )
        else:
            record["live_check"] = "not_run_by_contract"
        checked.append(record)

    ready = status_counts["ready"]
    unresolved = status_counts["accumulating"] + status_counts["blocked_external_evidence"]
    return {
        "schema_version": 1,
        "authority_rule": catalog["authority_rule"],
        "source_count": len(checked),
        "ready_count": ready,
        "unresolved_count": unresolved,
        "status_counts": status_counts,
        "sources": checked,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    result = build_health(catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(result))
    print(json.dumps({"sources": result["source_count"], "ready": result["ready_count"], "unresolved": result["unresolved_count"]}))


if __name__ == "__main__":
    main()
