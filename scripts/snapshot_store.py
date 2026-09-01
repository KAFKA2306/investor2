#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "data/input_ledger/snapshot_catalog.ndjson"
DEFAULT_REGISTRY = ROOT / "data/input_ledger/source_registry.json"
SOURCE_KINDS = {"api", "mcp", "official_web", "connector", "manual_import"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_observed_at(value: str) -> datetime:
    if len(value) == 10:
        parsed_date = date.fromisoformat(value)
        return datetime(parsed_date.year, parsed_date.month, parsed_date.day, tzinfo=timezone.utc)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("observed_at datetime must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def load_ndjson(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict[str, Any]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    schema_version = registry.get("schema_version")
    sources = registry.get("sources")
    if not isinstance(schema_version, str) or not schema_version:
        raise AssertionError("source registry is missing schema_version")
    if not isinstance(sources, dict):
        raise AssertionError("source registry must contain a sources object")

    merged_sources = dict(sources)
    fragment_root = path.with_name("source_registry.d")
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


def resolve_artifact(root: Path, artifact_path: str) -> Path:
    candidate = (root / artifact_path).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise AssertionError(f"artifact_path escapes repository root: {artifact_path}")
    return candidate


def infer_record_count(path: Path) -> int:
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, list):
            return len(value)
        if isinstance(value, dict) and isinstance(value.get("records"), list):
            return len(value["records"])
        return 1
    if path.suffix.lower() in {".ndjson", ".jsonl"}:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return 1


def required_snapshot_provenance(source_cfg: dict[str, Any]) -> list[str]:
    value = source_cfg.get("snapshot_required_provenance", [])
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise AssertionError("snapshot_required_provenance must be a list of non-empty strings")
    return value


def validate_provenance(provenance: dict[str, Any], source_cfg: dict[str, Any]) -> None:
    missing = [key for key in required_snapshot_provenance(source_cfg) if provenance.get(key) in (None, "", [])]
    if missing:
        raise AssertionError(f"missing required snapshot provenance: {missing}")
    source_urls = provenance.get("source_urls")
    if source_urls is not None:
        if not isinstance(source_urls, list) or not source_urls:
            raise AssertionError("source_urls must be a non-empty list when provided")
        if any(not isinstance(url, str) or not url.startswith("https://") for url in source_urls):
            raise AssertionError("source_urls must contain only https URLs")


def make_snapshot_id(dataset_id: str, reuse_key: str, observed_at: str, artifact_sha256: str) -> str:
    payload = f"{dataset_id}|{reuse_key}|{observed_at}|{artifact_sha256}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]


def build_entry(
    *,
    root: Path,
    registry: dict[str, Any],
    dataset_id: str,
    reuse_key: str,
    artifact_path: str,
    source: str,
    source_kind: str,
    observed_at: str,
    schema_version: str,
    provenance: dict[str, Any],
) -> dict[str, Any]:
    if source not in registry["sources"]:
        raise AssertionError(f"unregistered source: {source}")
    source_cfg = registry["sources"][source]
    if not source_cfg.get("enabled"):
        raise AssertionError(f"disabled source: {source}")
    if source_cfg.get("failure_mode") != "fail-closed":
        raise AssertionError(f"source must fail closed: {source}")
    if source_kind not in SOURCE_KINDS:
        raise AssertionError(f"unsupported source_kind: {source_kind}")
    parse_observed_at(observed_at)
    validate_provenance(provenance, source_cfg)

    artifact = resolve_artifact(root, artifact_path)
    if not artifact.is_file():
        raise AssertionError(f"artifact does not exist: {artifact_path}")
    artifact_sha256 = sha256_file(artifact)

    return {
        "snapshot_id": make_snapshot_id(dataset_id, reuse_key, observed_at, artifact_sha256),
        "dataset_id": dataset_id,
        "reuse_key": reuse_key,
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha256,
        "record_count": infer_record_count(artifact),
        "media_type": "application/json" if artifact.suffix.lower() == ".json" else "application/x-ndjson",
        "schema_version": schema_version,
        "source": source,
        "source_kind": source_kind,
        "observed_at": observed_at,
        "provenance": provenance,
        "status": "accepted",
    }


def audit_entry(entry: dict[str, Any], *, root: Path, registry: dict[str, Any]) -> dict[str, Any]:
    required = {
        "snapshot_id",
        "dataset_id",
        "reuse_key",
        "artifact_path",
        "artifact_sha256",
        "record_count",
        "schema_version",
        "source",
        "source_kind",
        "observed_at",
        "provenance",
        "status",
    }
    missing = sorted(required - entry.keys())
    if missing:
        raise AssertionError(f"snapshot entry missing fields: {missing}")
    if entry["status"] != "accepted":
        raise AssertionError("only accepted snapshots belong in the canonical catalog")
    if entry["source_kind"] not in SOURCE_KINDS:
        raise AssertionError(f"unsupported source_kind: {entry['source_kind']}")
    parse_observed_at(entry["observed_at"])

    source = entry["source"]
    if source not in registry["sources"]:
        raise AssertionError(f"unregistered source: {source}")
    source_cfg = registry["sources"][source]
    if not source_cfg.get("enabled"):
        raise AssertionError(f"disabled source accepted: {source}")
    if source_cfg.get("failure_mode") != "fail-closed":
        raise AssertionError(f"source must fail closed: {source}")
    validate_provenance(entry["provenance"], source_cfg)

    artifact = resolve_artifact(root, entry["artifact_path"])
    if not artifact.is_file():
        raise AssertionError(f"missing artifact: {entry['artifact_path']}")
    actual_hash = sha256_file(artifact)
    if actual_hash != entry["artifact_sha256"]:
        raise AssertionError(
            f"artifact SHA-256 mismatch for {entry['artifact_path']}: "
            f"{actual_hash} != {entry['artifact_sha256']}"
        )
    actual_count = infer_record_count(artifact)
    if actual_count != entry["record_count"]:
        raise AssertionError(
            f"record_count mismatch for {entry['artifact_path']}: "
            f"{actual_count} != {entry['record_count']}"
        )
    expected_id = make_snapshot_id(
        entry["dataset_id"], entry["reuse_key"], entry["observed_at"], entry["artifact_sha256"]
    )
    if entry["snapshot_id"] != expected_id:
        raise AssertionError(f"snapshot_id mismatch: {entry['snapshot_id']} != {expected_id}")

    return {
        "snapshot_id": entry["snapshot_id"],
        "dataset_id": entry["dataset_id"],
        "reuse_key": entry["reuse_key"],
        "artifact_path": entry["artifact_path"],
        "record_count": entry["record_count"],
        "artifact_sha256": actual_hash,
        "status": "PASS",
    }


def audit_catalog(
    *,
    root: Path = ROOT,
    catalog_path: Path | None = None,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    catalog = catalog_path or (root / "data/input_ledger/snapshot_catalog.ndjson")
    registry_file = registry_path or (root / "data/input_ledger/source_registry.json")
    entries = load_ndjson(catalog)
    if not entries:
        raise AssertionError("snapshot catalog must not be empty")
    ids = [entry.get("snapshot_id") for entry in entries]
    if len(ids) != len(set(ids)):
        raise AssertionError("duplicate snapshot_id")
    coordinates = [(entry.get("reuse_key"), entry.get("observed_at")) for entry in entries]
    if len(coordinates) != len(set(coordinates)):
        raise AssertionError("duplicate reuse_key + observed_at snapshot")
    registry = load_registry(registry_file)
    results = [audit_entry(entry, root=root, registry=registry) for entry in entries]
    return {
        "schema_version": "investor2.external-snapshot-catalog-audit.v1",
        "status": "PASS",
        "snapshots": results,
    }


def latest_snapshot(
    *,
    reuse_key: str,
    root: Path = ROOT,
    catalog_path: Path | None = None,
) -> dict[str, Any]:
    catalog = catalog_path or (root / "data/input_ledger/snapshot_catalog.ndjson")
    matches = [entry for entry in load_ndjson(catalog) if entry.get("reuse_key") == reuse_key]
    if not matches:
        raise LookupError(f"no accepted snapshot for reuse_key: {reuse_key}")
    return max(matches, key=lambda entry: parse_observed_at(entry["observed_at"]))


def append_entry(entry: dict[str, Any], catalog_path: Path = DEFAULT_CATALOG) -> None:
    entries = load_ndjson(catalog_path)
    if any(existing.get("snapshot_id") == entry["snapshot_id"] for existing in entries):
        raise AssertionError(f"snapshot already registered: {entry['snapshot_id']}")
    if any(
        existing.get("reuse_key") == entry["reuse_key"] and existing.get("observed_at") == entry["observed_at"]
        for existing in entries
    ):
        raise AssertionError("reuse_key + observed_at already registered")
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    with catalog_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def parse_provenance(raw: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise AssertionError("provenance JSON must be an object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Register, audit, and resolve reusable external data snapshots.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Register an already-materialized artifact.")
    register.add_argument("--dataset-id", required=True)
    register.add_argument("--reuse-key", required=True)
    register.add_argument("--artifact-path", required=True)
    register.add_argument("--source", required=True)
    register.add_argument("--source-kind", choices=sorted(SOURCE_KINDS), required=True)
    register.add_argument("--observed-at", required=True)
    register.add_argument("--schema-version", required=True)
    register.add_argument("--provenance-json", required=True)

    latest = subparsers.add_parser("latest", help="Resolve the newest accepted snapshot for a reuse key.")
    latest.add_argument("--reuse-key", required=True)

    subparsers.add_parser("audit", help="Fail closed if any catalog entry is missing, mutated, or unregistered.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "audit":
        print(json.dumps(audit_catalog(), ensure_ascii=False, sort_keys=True))
        return
    if args.command == "latest":
        print(json.dumps(latest_snapshot(reuse_key=args.reuse_key), ensure_ascii=False, sort_keys=True))
        return

    registry = load_registry()
    entry = build_entry(
        root=ROOT,
        registry=registry,
        dataset_id=args.dataset_id,
        reuse_key=args.reuse_key,
        artifact_path=args.artifact_path,
        source=args.source,
        source_kind=args.source_kind,
        observed_at=args.observed_at,
        schema_version=args.schema_version,
        provenance=parse_provenance(args.provenance_json),
    )
    append_entry(entry)
    print(json.dumps(entry, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
