#!/usr/bin/env python3
"""Verify finAnalist AI Economics without copying its domain facts."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "data" / "ark-big-ideas" / "ai-economics-source.json"
DEFAULT_OUTPUT = ROOT / "api" / "v1" / "ark-big-ideas" / "ai-economics-source-health.json"
UA = "investor2-ai-economics-source-health/1.0 github.com/KAFKA2306/investor2"


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def fetch_json(url: str) -> tuple[bytes, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read()
    if not raw:
        raise ValueError(f"empty canonical source: {url}")
    return raw, json.loads(raw)


def build(source: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "theme",
        "authority_rule",
        "repository",
        "canonical_url",
        "raw_url",
        "manifest_url",
        "issue_url",
        "minimum_observation_count",
    }
    missing = required - source.keys()
    if missing:
        raise ValueError(f"source missing fields: {sorted(missing)}")
    if source["repository"] != "KAFKA2306/finAnalist":
        raise ValueError("AI economics authority must remain KAFKA2306/finAnalist")

    index_raw, index = fetch_json(source["raw_url"])
    manifest_raw, manifest = fetch_json(source["manifest_url"])
    count = int(index.get("observation_count", -1))
    if count < int(source["minimum_observation_count"]):
        raise ValueError(f"observation_count regressed: {count}")
    if int(manifest.get("observation_count", -1)) != count:
        raise ValueError("index/manifest observation_count mismatch")
    digest = manifest.get("content_digest")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("manifest content_digest missing or invalid")

    return {
        "schema_version": 1,
        "theme": source["theme"],
        "authority_rule": source["authority_rule"],
        "repository": source["repository"],
        "canonical_url": source["canonical_url"],
        "raw_url": source["raw_url"],
        "manifest_url": source["manifest_url"],
        "issue_url": source["issue_url"],
        "live_check": "ok",
        "index_sha256": hashlib.sha256(index_raw).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "content_digest": digest,
        "updated_at": index.get("updated_at"),
        "observation_count": count,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    result = build(source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(result))
    print(json.dumps({"live_check": result["live_check"], "observations": result["observation_count"], "content_digest": result["content_digest"]}))


if __name__ == "__main__":
    main()
