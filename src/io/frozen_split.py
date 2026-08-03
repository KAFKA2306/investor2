from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_MANIFEST_PATH = Path("data/benchmarks/industry_prediction_frozen_split.json")
DEFAULT_SOURCE_PATH = Path(
    "cache/benchmarks/edinet-bench/industry_prediction/train-00000-of-00001.parquet"
)


def canonical_json(value: Any) -> bytes:
    """Serialize evidence deterministically for hashing and audit records."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_sha256(manifest: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(manifest)).hexdigest()


def load_frozen_split_manifest(
    path: Path = DEFAULT_MANIFEST_PATH,
) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Frozen split manifest not found: {path}")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1:
        raise ValueError("Frozen split manifest schema_version must be 1")
    source = manifest.get("source")
    policy = manifest.get("policy")
    if not isinstance(source, dict) or not isinstance(policy, dict):
        raise ValueError("Frozen split manifest requires source and policy objects")
    required_source = {"dataset", "config", "split", "revision", "sha256", "row_count"}
    required_policy = {
        "algorithm",
        "seed",
        "evaluation_fraction",
        "id_column",
        "group_column",
    }
    if missing := required_source - set(source):
        raise ValueError(f"Frozen split source metadata is incomplete: {sorted(missing)}")
    if missing := required_policy - set(policy):
        raise ValueError(f"Frozen split policy is incomplete: {sorted(missing)}")
    if policy["algorithm"] != "stratified_sha256_rank_v1":
        raise ValueError(f"Unsupported frozen split algorithm: {policy['algorithm']}")
    fraction = float(policy["evaluation_fraction"])
    if not 0 < fraction < 1:
        raise ValueError("evaluation_fraction must be between 0 and 1")
    return manifest


def validate_source_file(source_path: Path, manifest: dict[str, Any]) -> str:
    if not source_path.exists():
        raise FileNotFoundError(f"EDINET-Bench source file not found: {source_path}")
    actual = sha256_file(source_path)
    expected = str(manifest["source"]["sha256"])
    if actual != expected:
        raise ValueError(
            "EDINET-Bench source SHA256 does not match the frozen manifest: "
            f"expected={expected}, actual={actual}"
        )
    return actual


def _rank(seed: int, group: str, doc_id: str) -> str:
    return hashlib.sha256(f"{seed}\0{group}\0{doc_id}".encode()).hexdigest()


def build_frozen_split(
    frame: pd.DataFrame,
    manifest: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    policy = manifest["policy"]
    id_column = str(policy["id_column"])
    group_column = str(policy["group_column"])
    required = {id_column, group_column}
    if missing := required - set(frame.columns):
        raise ValueError(f"Industry dataset is missing columns: {sorted(missing)}")

    normalized = frame.copy()
    normalized[id_column] = normalized[id_column].astype(str)
    normalized[group_column] = normalized[group_column].astype(str)
    if normalized[id_column].isna().any() or (normalized[id_column].str.len() == 0).any():
        raise ValueError("Every industry row must have a non-empty doc_id")
    if normalized[id_column].duplicated().any():
        duplicates = sorted(normalized.loc[normalized[id_column].duplicated(), id_column].unique())
        raise ValueError(f"Duplicate doc_id values in industry dataset: {duplicates[:10]}")

    expected_rows = int(manifest["source"]["row_count"])
    if len(normalized) != expected_rows:
        raise ValueError(
            "Industry dataset row count does not match the frozen manifest: "
            f"expected={expected_rows}, actual={len(normalized)}"
        )

    seed = int(policy["seed"])
    fraction = float(policy["evaluation_fraction"])
    evaluation_ids: set[str] = set()
    class_counts: dict[str, dict[str, int]] = {}

    for group, group_frame in normalized.groupby(group_column, sort=True):
        ranked_ids = sorted(
            group_frame[id_column].tolist(),
            key=lambda doc_id: (_rank(seed, str(group), doc_id), doc_id),
        )
        size = len(ranked_ids)
        if size <= 1:
            evaluation_count = 0
        else:
            proposed = int(size * fraction + 0.5)
            evaluation_count = max(1, min(size - 1, proposed))
        evaluation_ids.update(ranked_ids[:evaluation_count])
        class_counts[str(group)] = {
            "total": size,
            "development": size - evaluation_count,
            "frozen_evaluation": evaluation_count,
        }

    normalized["_frozen_rank"] = [
        _rank(seed, group, doc_id)
        for group, doc_id in zip(
            normalized[group_column].astype(str),
            normalized[id_column].astype(str),
            strict=True,
        )
    ]
    evaluation = normalized[normalized[id_column].isin(evaluation_ids)].sort_values(
        [group_column, "_frozen_rank", id_column]
    )
    development = normalized[~normalized[id_column].isin(evaluation_ids)].sort_values(
        [group_column, "_frozen_rank", id_column]
    )

    development_ids = set(development[id_column])
    frozen_ids = set(evaluation[id_column])
    if development_ids & frozen_ids:
        raise AssertionError("Development and frozen evaluation doc_id sets overlap")
    if development_ids | frozen_ids != set(normalized[id_column]):
        raise AssertionError("Frozen split does not cover the complete industry dataset")

    evidence = {
        "split_id": manifest["split_id"],
        "split_name": "frozen_evaluation",
        "algorithm": policy["algorithm"],
        "seed": seed,
        "evaluation_fraction": fraction,
        "manifest_sha256": manifest_sha256(manifest),
        "source": manifest["source"],
        "class_counts": class_counts,
        "development_count": len(development),
        "frozen_evaluation_count": len(evaluation),
        "development_doc_ids_sha256": hashlib.sha256(
            canonical_json(sorted(development_ids))
        ).hexdigest(),
        "frozen_evaluation_doc_ids_sha256": hashlib.sha256(
            canonical_json(sorted(frozen_ids))
        ).hexdigest(),
        "frozen_evaluation_doc_ids": evaluation[id_column].tolist(),
    }
    return (
        development.drop(columns=["_frozen_rank"]),
        evaluation.drop(columns=["_frozen_rank"]),
        evidence,
    )
