from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_source_registry(base_path: Path, fragments_dir: Path | None = None) -> dict[str, Any]:
    base = json.loads(base_path.read_text(encoding="utf-8"))
    schema_version = base.get("schema_version")
    sources = base.get("sources")
    if not isinstance(schema_version, str) or not schema_version:
        raise AssertionError("source registry is missing schema_version")
    if not isinstance(sources, dict):
        raise AssertionError("source registry must contain a sources object")

    merged_sources = dict(sources)
    fragment_root = fragments_dir or base_path.with_name("source_registry.d")
    if fragment_root.is_dir():
        for fragment_path in sorted(fragment_root.glob("*.json")):
            fragment = json.loads(fragment_path.read_text(encoding="utf-8"))
            if fragment.get("schema_version") != schema_version:
                raise AssertionError(f"source registry fragment schema mismatch: {fragment_path.name}")
            fragment_sources = fragment.get("sources")
            if not isinstance(fragment_sources, dict) or not fragment_sources:
                raise AssertionError(f"source registry fragment must contain sources: {fragment_path.name}")
            duplicate_ids = sorted(set(merged_sources) & set(fragment_sources))
            if duplicate_ids:
                raise AssertionError(f"duplicate source registry ids: {duplicate_ids}")
            merged_sources.update(fragment_sources)

    return {"schema_version": schema_version, "sources": merged_sources}
