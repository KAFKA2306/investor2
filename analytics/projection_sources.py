from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class ProjectionSourceError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ProjectionSourceError(f"{path} must contain a JSON object")
    return value


def load_snapshot_rows(root: Path) -> list[dict[str, Any]]:
    path = root / "data/input_ledger/snapshot_catalog.ndjson"
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ProjectionSourceError(f"{path}:{line_number} must be a JSON object")

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
        missing = sorted(required - value.keys())
        if missing:
            raise ProjectionSourceError(
                f"{path}:{line_number} missing snapshot fields: {missing}"
            )
        if value["status"] != "accepted":
            raise ProjectionSourceError(
                f"{path}:{line_number} contains non-accepted snapshot status"
            )

        rows.append(
            {
                "snapshot_id": str(value["snapshot_id"]),
                "dataset_id": str(value["dataset_id"]),
                "reuse_key": str(value["reuse_key"]),
                "artifact_path": str(value["artifact_path"]),
                "artifact_sha256": str(value["artifact_sha256"]),
                "record_count": int(value["record_count"]),
                "schema_version": str(value["schema_version"]),
                "source": str(value["source"]),
                "source_kind": str(value["source_kind"]),
                "observed_at": str(value["observed_at"]),
                "status": str(value["status"]),
                "provenance_json": canonical_json(value["provenance"]),
            }
        )

    _require_rows("snapshot catalog", rows)
    _require_unique("snapshot_id", rows, key="snapshot_id")
    coordinates = [(row["reuse_key"], row["observed_at"]) for row in rows]
    if len(coordinates) != len(set(coordinates)):
        raise ProjectionSourceError("snapshot catalog has duplicate reuse_key + observed_at")
    return rows


def load_hypothesis_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "data/hypothesis_lab/hypotheses").glob("*.json")):
        value = read_object(path)
        hypothesis_id = value.get("hypothesis_id")
        schema_version = value.get("schema_version")
        thesis = value.get("thesis")
        falsifiers = value.get("falsifiers")
        if not isinstance(hypothesis_id, str) or not hypothesis_id:
            raise ProjectionSourceError(f"{path} is missing hypothesis_id")
        if not isinstance(schema_version, (str, int)) or str(schema_version) == "":
            raise ProjectionSourceError(f"{path} is missing schema_version")
        if not isinstance(thesis, str) or not thesis:
            raise ProjectionSourceError(f"{path} is missing thesis")
        if not isinstance(falsifiers, list) or not falsifiers:
            raise ProjectionSourceError(f"{path} must contain falsifiers")

        rows.append(
            {
                "hypothesis_id": hypothesis_id,
                "schema_version": str(schema_version),
                "thesis": thesis,
                "falsifier_count": len(falsifiers),
                "path": path.relative_to(root).as_posix(),
                "artifact_sha256": sha256_file(path),
                "raw_json": canonical_json(value),
            }
        )

    _require_rows("hypotheses", rows)
    _require_unique("hypothesis_id", rows, key="hypothesis_id")
    return rows


def load_oos_result_rows(root: Path) -> list[dict[str, Any]]:
    paths = list(sorted((root / "docs/research/results").glob("**/summary.json")))
    legacy = root / "docs/research/post_publication_momentum_oos.json"
    if legacy.is_file():
        paths.append(legacy)

    rows: list[dict[str, Any]] = []
    for path in sorted(set(paths)):
        value = read_object(path)
        result_id = path.relative_to(root).as_posix()
        verdict = value.get("verdict")
        research_question = value.get("research_question") or value.get("study") or ""
        as_of = value.get("as_of") or value.get("publication_month") or ""
        rows.append(
            {
                "result_id": result_id,
                "path": result_id,
                "verdict": str(verdict) if verdict is not None else "UNSPECIFIED",
                "research_question": str(research_question),
                "as_of": str(as_of),
                "artifact_sha256": sha256_file(path),
                "raw_json": canonical_json(value),
            }
        )

    _require_rows("OOS results", rows)
    _require_unique("result_id", rows, key="result_id")
    return rows


def load_benchmark_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((root / "data/benchmarks").glob("*.json")):
        value = read_object(path)
        source = value.get("source")
        if source is None:
            source = {}
        if not isinstance(source, dict):
            raise ProjectionSourceError(f"{path} source must be an object")

        benchmark_id = value.get("split_id") or path.stem
        schema_version = value.get("schema_version")
        if not isinstance(benchmark_id, str) or not benchmark_id:
            raise ProjectionSourceError(f"{path} is missing benchmark identity")
        if not isinstance(schema_version, (str, int)) or str(schema_version) == "":
            raise ProjectionSourceError(f"{path} is missing schema_version")

        row_count = source.get("row_count")
        rows.append(
            {
                "benchmark_id": benchmark_id,
                "schema_version": str(schema_version),
                "source_dataset": str(source.get("dataset") or ""),
                "source_revision": str(source.get("revision") or ""),
                "row_count": int(row_count) if row_count is not None else None,
                "path": path.relative_to(root).as_posix(),
                "artifact_sha256": sha256_file(path),
                "raw_json": canonical_json(value),
            }
        )

    _require_rows("benchmark contracts", rows)
    _require_unique("benchmark_id", rows, key="benchmark_id")
    return rows


def load_projection_rows(root: Path) -> dict[str, list[dict[str, Any]]]:
    root = root.resolve()
    return {
        "input_snapshots": load_snapshot_rows(root),
        "hypotheses": load_hypothesis_rows(root),
        "oos_results": load_oos_result_rows(root),
        "benchmark_contracts": load_benchmark_rows(root),
    }


def _require_rows(label: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ProjectionSourceError(f"{label} must not be empty")


def _require_unique(label: str, rows: list[dict[str, Any]], *, key: str) -> None:
    values = [row[key] for row in rows]
    if len(values) != len(set(values)):
        raise ProjectionSourceError(f"{label} contains duplicate {key}")
