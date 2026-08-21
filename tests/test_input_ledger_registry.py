from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.io.input_ledger.registry import load_source_registry


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_registry_merges_fragments_without_overrides(tmp_path: Path) -> None:
    base = tmp_path / "source_registry.json"
    fragments = tmp_path / "source_registry.d"
    _write(base, {"schema_version": "v1", "sources": {"base": {"enabled": True}}})
    _write(fragments / "polymarket.json", {"schema_version": "v1", "sources": {"polymarket": {"enabled": True}}})

    registry = load_source_registry(base)

    assert sorted(registry["sources"]) == ["base", "polymarket"]


def test_registry_rejects_duplicate_source_ids(tmp_path: Path) -> None:
    base = tmp_path / "source_registry.json"
    fragments = tmp_path / "source_registry.d"
    _write(base, {"schema_version": "v1", "sources": {"same": {"enabled": True}}})
    _write(fragments / "duplicate.json", {"schema_version": "v1", "sources": {"same": {"enabled": True}}})

    with pytest.raises(AssertionError, match="duplicate source registry ids"):
        load_source_registry(base)


def test_registry_rejects_fragment_schema_mismatch(tmp_path: Path) -> None:
    base = tmp_path / "source_registry.json"
    fragments = tmp_path / "source_registry.d"
    _write(base, {"schema_version": "v1", "sources": {"base": {"enabled": True}}})
    _write(fragments / "wrong.json", {"schema_version": "v2", "sources": {"new": {"enabled": True}}})

    with pytest.raises(AssertionError, match="schema mismatch"):
        load_source_registry(base)
