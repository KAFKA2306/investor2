from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/research/warin_2101_02044_v4_experiment_matrix.json"
REGISTRY = ROOT / "docs/research/2021_arxiv_finance_registry.json"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def by_id(matrix: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = matrix["experiments"]
    ids = [row["id"] for row in rows]
    assert len(ids) == len(set(ids))
    return {row["id"]: row for row in rows}


def test_matrix_is_partial_and_never_paper_wide_reproduced() -> None:
    matrix = load(MATRIX)
    assert matrix["paper_wide_reproduction_state"] == "PARTIAL"
    assert matrix["paper_wide_empirical_verdict"] == "NOT_CLAIMED"
    statuses = {row["status"] for row in matrix["experiments"]}
    assert statuses <= {"REPRODUCED", "FAILED", "BLOCKED", "NOT_RUN"}
    assert "FAILED" in statuses
    assert "BLOCKED" in statuses
    assert "NOT_RUN" in statuses


def test_table1_direct_points_preserve_actual_verdicts_and_hashes() -> None:
    matrix = load(MATRIX)
    rows = by_id(matrix)
    expected = {
        "s3_2_table1_dim4_direct_beta005": {
            "status": "FAILED",
            "mean": 1.9132914229382743,
            "variance": 5.697546729432851,
        },
        "s3_2_table1_dim4_direct_beta02": {
            "status": "FAILED",
            "mean": 1.47430220808855,
            "variance": 0.9581149446363684,
        },
        "s3_2_table1_dim4_direct_beta2": {"status": "REPRODUCED"},
    }
    for row_id, target in expected.items():
        row = rows[row_id]
        assert row["status"] == target["status"]
        if "mean" in target:
            assert row["observed"]["mean"] == target["mean"]
            assert row["observed"]["variance"] == target["variance"]
            assert row["observed"]["analytical_match"] is True
            assert row["observed"]["neural_match"] is False
            for path_key, hash_key in (
                ("report", "report_sha256"),
                ("training_trace", "training_trace_sha256"),
                ("model_state", "model_state_sha256"),
            ):
                path = ROOT / row[path_key]
                assert path.is_file()
                assert sha256(path) == row[hash_key]


def test_table9_selected_scope_is_reproduced_without_promoting_remaining_tables() -> None:
    rows = by_id(load(MATRIX))
    selected = rows["s4_3_1_tables9_10_dim4_models1_4_beta0959"]
    remaining = rows["s4_3_1_tables11_14_dim4_remaining_constraint_models"]
    assert selected["status"] == "REPRODUCED"
    assert selected["risk_parameter"] == {"beta": 0.959}
    assert selected["protocol"] == "docs/research/protocols/warin_2101_02044_v4_table9_beta0959.json"
    assert selected["run"] == "docs/research/runs/warin_2101_02044_v4_table9_beta0959_seed2306/summary.json"
    assert remaining["status"] == "NOT_RUN"


def test_blocked_rows_have_machine_readable_reasons() -> None:
    matrix = load(MATRIX)
    for row in matrix["experiments"]:
        if row["status"] == "BLOCKED":
            assert row.get("reason_codes")
        if row["status"] in {"REPRODUCED", "FAILED"}:
            assert row.get("protocol") or row.get("run")


def test_registry_exposes_scoped_not_paper_wide_verdict() -> None:
    registry = load(REGISTRY)
    warin = next(row for row in registry["papers"] if row["arxiv_id"] == "2101.02044")
    assert warin["empirical_reproduction_state"] == "EMPIRICALLY_RUN"
    assert warin["empirical_verdict"] == "REPRODUCED"
    assert warin["empirical_verdict_scope"] == "SECTION_3_2_TABLE_1_BETA_2_LEGACY_PRIMARY_MANIFEST_ONLY"
    assert warin["paper_wide_reproduction_state"] == "PARTIAL"
    assert warin["paper_wide_empirical_verdict"] == "NOT_CLAIMED"
    assert warin["table1_direct_point_verdicts"] == {
        "beta_0_05": "FAILED",
        "beta_0_2": "FAILED",
        "beta_2_0": "REPRODUCED",
    }
    assert warin["experiment_matrix"] == MATRIX.relative_to(ROOT).as_posix()


def test_registry_materialized_hashes_cover_failed_runs() -> None:
    registry = load(REGISTRY)
    rows = {
        (row["run_id"], row["kind"]): row
        for row in registry["materialized_artifacts"]
        if row["paper_id"] == "warin_2101_02044"
    }
    for run_id in ("v4_table1_beta005_seed2306", "v4_table1_beta02_seed2306"):
        for kind in ("empirical_evaluation", "training_trace", "trained_state"):
            row = rows[(run_id, kind)]
            path = ROOT / row["path"]
            assert path.is_file()
            assert sha256(path) == row["sha256"]
