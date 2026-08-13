#!/usr/bin/env python3
"""Validate selected 2021 arXiv finance papers and deterministic method contracts.

The paper selection is anchored to the repository's frozen 2021 q-fin metadata
universe. Passing a method contract means only that a small mechanism stated by the
paper has a working deterministic implementation. It does not reproduce the paper's
empirical performance claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
ARXIV_URL = re.compile(r"https://arxiv\.org/abs/(?P<id>\d{4}\.\d{4,5})$")
SHA256 = re.compile(r"[0-9a-f]{64}")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_to_simplex(values: list[float]) -> list[float]:
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values, reverse=True)
    cumulative = 0.0
    theta = 0.0
    found = False
    for index, value in enumerate(ordered, start=1):
        cumulative += value
        candidate = (cumulative - 1.0) / index
        if value - candidate > 0.0:
            theta = candidate
            found = True
    if not found:
        raise ValueError("simplex projection failed")
    return [max(value - theta, 0.0) for value in values]


def invest_cash_reward(
    *,
    action: int,
    previous_action: int,
    asset_next_return: float,
    cross_section_next_returns: list[float],
    transaction_cost: float,
) -> float:
    if action not in {0, 1} or previous_action not in {0, 1}:
        raise ValueError("actions must be binary")
    if not cross_section_next_returns:
        raise ValueError("cross section must not be empty")
    if action == 1:
        return asset_next_return - (1 - previous_action) * transaction_cost
    return sum(cross_section_next_returns) / len(cross_section_next_returns)


def realized_variance(values: list[float]) -> float:
    return sum(value * value for value in values)


def multiscale_realized_variance(values: list[float], block_sizes: list[int]) -> dict[int, list[float]]:
    if not values or any(size <= 0 for size in block_sizes):
        raise ValueError("non-empty values and positive block sizes are required")
    return {
        size: [realized_variance(values[start : start + size]) for start in range(0, len(values), size)]
        for size in block_sizes
    }


def combine_relations(relations: list[list[list[float]]], weights: list[float]) -> list[list[float]]:
    if not relations or len(relations) != len(weights):
        raise ValueError("one weight is required per relation")
    n = len(relations[0])
    if n == 0 or any(len(matrix) != n or any(len(row) != n for row in matrix) for matrix in relations):
        raise ValueError("relations must be non-empty square matrices with equal shape")
    mixed = [[0.0] * n for _ in range(n)]
    for matrix, weight in zip(relations, weights, strict=True):
        for i in range(n):
            for j in range(n):
                mixed[i][j] += weight * matrix[i][j]
    for i, row in enumerate(mixed):
        total = sum(row)
        if total <= 0:
            raise ValueError(f"relation row {i} has no mass")
        mixed[i] = [value / total for value in row]
    return mixed


def graph_message(adjacency: list[list[float]], features: list[float]) -> list[float]:
    if len(adjacency) != len(features):
        raise ValueError("feature count must equal graph size")
    return [sum(weight * value for weight, value in zip(row, features, strict=True)) for row in adjacency]


def _warin() -> dict[str, Any]:
    raw = [-0.2, 0.2, 0.7, 0.4]
    weights = project_to_simplex(raw)
    passed = min(weights) >= 0.0 and math.isclose(sum(weights), 1.0, abs_tol=1e-12)
    return {"passed": passed, "observed": {"weights": weights, "weight_sum": sum(weights)}}


def _pigorsch() -> dict[str, Any]:
    cross_section = [0.01, -0.02, 0.03]
    entry = invest_cash_reward(action=1, previous_action=0, asset_next_return=0.03, cross_section_next_returns=cross_section, transaction_cost=0.001)
    hold = invest_cash_reward(action=1, previous_action=1, asset_next_return=0.03, cross_section_next_returns=cross_section, transaction_cost=0.001)
    cash = invest_cash_reward(action=0, previous_action=1, asset_next_return=0.03, cross_section_next_returns=cross_section, transaction_cost=0.001)
    expected_cash = sum(cross_section) / len(cross_section)
    passed = math.isclose(entry, 0.029, abs_tol=1e-12) and math.isclose(hold, 0.03, abs_tol=1e-12) and math.isclose(cash, expected_cash, abs_tol=1e-12)
    return {"passed": passed, "observed": {"entry_reward": entry, "hold_reward": hold, "cash_reward": cash}}


def _liao() -> dict[str, Any]:
    values = [0.01, -0.02, 0.015, -0.005, 0.012, -0.008, 0.004, -0.006]
    scales = multiscale_realized_variance(values, [1, 2, 4, 8])
    total = realized_variance(values)
    conserved = all(math.isclose(sum(buckets), total, abs_tol=1e-15) for buckets in scales.values())
    passed = conserved and [len(scales[size]) for size in (1, 2, 4, 8)] == [8, 4, 2, 1]
    return {"passed": passed, "observed": {"total_realized_variance": total, "bucket_counts": {str(k): len(v) for k, v in scales.items()}}}


def _chen_robert() -> dict[str, Any]:
    identity = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    sector = [[1.0, 1.0, 0.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0]]
    adjacency = combine_relations([identity, sector], [0.25, 0.75])
    message = graph_message(adjacency, [0.1, 0.5, 0.9])
    passed = all(math.isclose(sum(row), 1.0, abs_tol=1e-12) for row in adjacency) and len(message) == 3
    return {"passed": passed, "observed": {"row_sums": [sum(row) for row in adjacency], "message": message}}


VALIDATORS: dict[str, Callable[[], dict[str, Any]]] = {
    "long_only_simplex_projection": _warin,
    "invest_cash_reward": _pigorsch,
    "multiscale_realized_variance": _liao,
    "multi_relation_graph_aggregation": _chen_robert,
}


def load_discovery_universe(registry: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    discovery = registry.get("discovery_universe")
    if not isinstance(discovery, dict):
        raise ValueError("discovery_universe is required")
    path = ROOT / str(discovery.get("path", ""))
    if not path.is_file():
        raise ValueError(f"frozen discovery universe is missing: {path}")
    actual_hash = file_sha256(path)
    if actual_hash != discovery.get("sha256"):
        raise ValueError(f"discovery universe SHA-256 mismatch: {actual_hash}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("record_count") != discovery.get("record_count") or len(data.get("records", [])) != discovery.get("record_count"):
        raise ValueError("discovery universe record_count mismatch")
    if data.get("schema_version") != discovery.get("schema_version"):
        raise ValueError("discovery universe schema_version mismatch")
    records = data["records"]
    by_id = {row["arxiv_id"]: row for row in records}
    if len(by_id) != len(records):
        raise ValueError("discovery universe contains duplicate arXiv IDs")
    return data, by_id


def validate_registry(registry: dict[str, Any]) -> dict[str, Any]:
    if registry.get("schema_version") != 1:
        raise ValueError("unsupported schema_version")
    discovery_data, discovery_by_id = load_discovery_universe(registry)
    storage = registry.get("canonical_storage", {})
    template = storage.get("content_addressed_uri_template", "")
    for token in ("{bucket}", "{arxiv_id}", "{sha256}", "{filename}"):
        if token not in template:
            raise ValueError(f"storage URI template missing {token}")
    papers = registry.get("papers")
    if not isinstance(papers, list) or not papers:
        raise ValueError("papers must be a non-empty list")
    ids: set[str] = set()
    for paper in papers:
        paper_id = paper.get("id")
        if not isinstance(paper_id, str) or not paper_id or paper_id in ids:
            raise ValueError("paper ids must be unique non-empty strings")
        ids.add(paper_id)
        match = ARXIV_URL.fullmatch(str(paper.get("source_url", "")))
        if not match or match.group("id") != paper.get("arxiv_id"):
            raise ValueError(f"invalid arXiv primary URL for {paper_id}")
        if not str(paper.get("first_submitted", "")).startswith("2021-"):
            raise ValueError(f"{paper_id} is not a 2021 first submission")
        if paper.get("source_metadata_state") != "VERIFIED_PRIMARY_AND_FROZEN_UNIVERSE":
            raise ValueError(f"{paper_id} primary/frozen metadata is not verified")
        frozen = discovery_by_id.get(paper["arxiv_id"])
        if frozen is None:
            raise ValueError(f"{paper_id} is missing from frozen discovery universe")
        expected_fields = {
            "title": paper["title"],
            "authors": paper["authors"],
            "primary_category": paper["primary_category"],
        }
        for field, expected in expected_fields.items():
            if frozen.get(field) != expected:
                raise ValueError(f"{paper_id} frozen {field} mismatch")
        if str(frozen.get("published", ""))[:10] != paper["first_submitted"]:
            raise ValueError(f"{paper_id} frozen first-submitted date mismatch")
        if paper.get("method_contract") not in VALIDATORS:
            raise ValueError(f"unknown method contract for {paper_id}")
        if paper.get("empirical_reproduction_state") not in {"NOT_RUN", "NOT_CONFIRMED", "VERIFIED"}:
            raise ValueError(f"unknown empirical reproduction state for {paper_id}")
    for artifact in registry.get("materialized_artifacts", []):
        if artifact.get("paper_id") not in ids:
            raise ValueError("artifact references unknown paper")
        if not SHA256.fullmatch(str(artifact.get("sha256", ""))):
            raise ValueError("materialized artifact requires SHA-256")
        hf_uri = str(artifact.get("hf_uri", ""))
        if artifact["sha256"] not in hf_uri or not hf_uri.startswith("hf://buckets/"):
            raise ValueError("HF artifact URI must be content-addressed")
        for key in ("kind", "filename", "bytes", "observed_at", "source_url", "license"):
            if key not in artifact:
                raise ValueError(f"artifact missing {key}")
    return {
        "dataset_id": registry["discovery_universe"]["dataset_id"],
        "path": registry["discovery_universe"]["path"],
        "sha256": registry["discovery_universe"]["sha256"],
        "record_count": discovery_data["record_count"],
        "snapshot_id": registry["discovery_universe"]["snapshot_id"],
    }


def build_report(registry_path: Path) -> dict[str, Any]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    discovery_audit = validate_registry(registry)
    studies: list[dict[str, Any]] = []
    for paper in registry["papers"]:
        result = VALIDATORS[paper["method_contract"]]()
        studies.append({
            "id": paper["id"],
            "arxiv_id": paper["arxiv_id"],
            "title": paper["title"],
            "authors": paper["authors"],
            "first_submitted": paper["first_submitted"],
            "primary_category": paper["primary_category"],
            "source_url": paper["source_url"],
            "source_metadata_state": paper["source_metadata_state"],
            "paper_claim": paper["paper_claim"],
            "implementation_scope": paper["implementation_scope"],
            "method_contract": paper["method_contract"],
            "method_contract_state": "PASS" if result["passed"] else "FAIL",
            "method_observed": result["observed"],
            "empirical_reproduction_state": paper["empirical_reproduction_state"],
            "artifact_state": "MATERIALIZED" if any(a["paper_id"] == paper["id"] for a in registry["materialized_artifacts"]) else "NOT_MATERIALIZED",
            "reproduction_verdict": "METHOD_ONLY" if result["passed"] else "METHOD_CONTRACT_FAIL",
            "unreproduced_evidence": paper["unreproduced_evidence"],
        })
    return {
        "suite": "2021 arXiv finance reproduction queue",
        "discovery_universe": discovery_audit,
        "canonical_storage": registry["canonical_storage"],
        "summary": {
            "indexed": len(studies),
            "method_contract_pass": sum(study["method_contract_state"] == "PASS" for study in studies),
            "materialized": sum(study["artifact_state"] == "MATERIALIZED" for study in studies),
            "empirically_reproduced": sum(study["empirical_reproduction_state"] in {"NOT_CONFIRMED", "VERIFIED"} for study in studies),
        },
        "papers": studies,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, default=ROOT / "docs" / "research" / "2021_arxiv_finance_registry.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(args.registry)
    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
