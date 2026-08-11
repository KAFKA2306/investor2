from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.snapshot_store import (
    audit_catalog,
    build_entry,
    latest_snapshot,
    load_registry,
    make_snapshot_id,
)


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_catalog(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for entry in entries),
        encoding="utf-8",
    )


def make_registry(path: Path) -> None:
    write_json(
        path,
        {
            "schema_version": "test",
            "sources": {
                "test_mcp": {
                    "enabled": True,
                    "failure_mode": "fail-closed",
                    "snapshot_required_provenance": [
                        "tool",
                        "operation",
                        "query_or_scope",
                        "retrieved_at",
                        "source_urls",
                    ],
                }
            },
        },
    )


def test_repository_snapshot_catalog_passes() -> None:
    result = audit_catalog()
    assert result["status"] == "PASS"
    assert any(item["reuse_key"] == "jr_west/ureshito/eps-baseline" for item in result["snapshots"])


def test_build_entry_is_content_addressed(tmp_path: Path) -> None:
    registry_path = tmp_path / "data/input_ledger/source_registry.json"
    artifact = tmp_path / "data/example.json"
    make_registry(registry_path)
    write_json(artifact, [{"id": 1}, {"id": 2}])

    entry = build_entry(
        root=tmp_path,
        registry=load_registry(registry_path),
        dataset_id="example",
        reuse_key="example/latest",
        artifact_path="data/example.json",
        source="test_mcp",
        source_kind="mcp",
        observed_at="2026-08-11T11:00:00+09:00",
        schema_version="example.v1",
        provenance={
            "tool": "Example MCP",
            "operation": "compare",
            "query_or_scope": "two records",
            "retrieved_at": "2026-08-11T11:00:00+09:00",
            "source_urls": ["https://example.com/source"],
        },
    )

    expected_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert entry["artifact_sha256"] == expected_sha
    assert entry["record_count"] == 2
    assert entry["snapshot_id"] == make_snapshot_id(
        "example", "example/latest", "2026-08-11T11:00:00+09:00", expected_sha
    )


def test_audit_fails_after_artifact_mutation(tmp_path: Path) -> None:
    registry_path = tmp_path / "data/input_ledger/source_registry.json"
    catalog_path = tmp_path / "data/input_ledger/snapshot_catalog.ndjson"
    artifact = tmp_path / "data/example.json"
    make_registry(registry_path)
    write_json(artifact, [{"id": 1}])

    entry = build_entry(
        root=tmp_path,
        registry=load_registry(registry_path),
        dataset_id="example",
        reuse_key="example/latest",
        artifact_path="data/example.json",
        source="test_mcp",
        source_kind="mcp",
        observed_at="2026-08-11",
        schema_version="example.v1",
        provenance={
            "tool": "Example MCP",
            "operation": "fetch",
            "query_or_scope": "one record",
            "retrieved_at": "2026-08-11",
            "source_urls": ["https://example.com/source"],
        },
    )
    write_catalog(catalog_path, [entry])
    write_json(artifact, [{"id": 999}])

    with pytest.raises(AssertionError, match="SHA-256 mismatch"):
        audit_catalog(root=tmp_path, catalog_path=catalog_path, registry_path=registry_path)


def test_latest_snapshot_selects_newest_observation(tmp_path: Path) -> None:
    catalog_path = tmp_path / "data/input_ledger/snapshot_catalog.ndjson"
    entries = [
        {"reuse_key": "example/latest", "observed_at": "2026-08-10", "snapshot_id": "old"},
        {"reuse_key": "example/latest", "observed_at": "2026-08-11T09:00:00+09:00", "snapshot_id": "new"},
    ]
    write_catalog(catalog_path, entries)

    result = latest_snapshot(reuse_key="example/latest", root=tmp_path, catalog_path=catalog_path)
    assert result["snapshot_id"] == "new"
