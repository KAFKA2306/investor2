from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "verify_2021_arxiv_methods.py"
SPEC = importlib.util.spec_from_file_location("verify_2021_arxiv_methods", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_2021_registry_separates_method_contract_from_empirical_run() -> None:
    report = MODULE.build_report(ROOT / "docs/research/catalogs/2021_arxiv_finance_registry.json")

    assert report["discovery_universe"] == {
        "dataset_id": "arxiv_qfin_2021_metadata",
        "path": "docs/research/data/arxiv_qfin_2021.json",
        "sha256": "a1ebbbd25ae65b5bce391ccb8ded1a27fa7c013102581251cc1f6ee4e73a948c",
        "record_count": 1132,
        "snapshot_id": "78a7a514d27762fd3891",
    }
    assert report["summary"] == {
        "indexed": 4,
        "method_contract_pass": 4,
        "materialized": 1,
        "empirically_run": 1,
        "empirically_reproduced": 1,
        "empirically_failed": 0,
        "empirically_blocked": 0,
        "empirically_not_run": 3,
    }
    by_id = {paper["arxiv_id"]: paper for paper in report["papers"]}
    assert set(by_id) == {"2101.02044", "2112.04755", "2112.01166", "2112.09015"}
    assert all(paper["source_metadata_state"] == "VERIFIED_PRIMARY" for paper in report["papers"])
    assert all(paper["frozen_universe_state"] == "VERIFIED" for paper in report["papers"])
    assert all(paper["method_contract_state"] == "PASS" for paper in report["papers"])

    warin = by_id["2101.02044"]
    assert warin["source_version"] == "v4"
    assert warin["empirical_reproduction_state"] == "EMPIRICALLY_RUN"
    assert warin["empirical_verdict"] == "REPRODUCED"
    assert warin["artifact_state"] == "MATERIALIZED"
    assert warin["reproduction_verdict"] == "REPRODUCED"
    assert warin["empirical_evidence_manifest"].endswith("/manifest.json")
    assert len(warin["empirical_evidence_manifest_sha256"]) == 64

    not_run = [paper for paper in report["papers"] if paper["arxiv_id"] != "2101.02044"]
    assert len(not_run) == 3
    assert all(paper["empirical_reproduction_state"] == "NOT_RUN" for paper in not_run)
    assert all(paper["empirical_verdict"] is None for paper in not_run)
    assert all(paper["artifact_state"] == "NOT_MATERIALIZED" for paper in not_run)
    assert all(paper["reproduction_verdict"] == "METHOD_ONLY" for paper in not_run)


def test_not_run_cannot_carry_empirical_verdict_or_evidence() -> None:
    invalid = {
        "id": "example",
        "empirical_reproduction_state": "NOT_RUN",
        "empirical_verdict": "REPRODUCED",
    }
    try:
        MODULE.validate_empirical_state(invalid)
    except ValueError as error:
        assert "NOT_RUN" in str(error)
    else:
        raise AssertionError("NOT_RUN must never be accepted with an empirical verdict")


def test_empirically_run_requires_evidence_manifest_and_hash() -> None:
    invalid = {
        "id": "example",
        "arxiv_id": "2101.02044",
        "empirical_reproduction_state": "EMPIRICALLY_RUN",
        "empirical_verdict": "REPRODUCED",
    }
    try:
        MODULE.validate_empirical_state(invalid)
    except ValueError as error:
        assert "evidence manifest" in str(error)
    else:
        raise AssertionError("EMPIRICALLY_RUN must fail closed without evidence")


def test_simplex_projection_preserves_long_only_unit_budget() -> None:
    weights = MODULE.project_to_simplex([-0.2, 0.2, 0.7, 0.4])
    assert min(weights) >= 0.0
    assert abs(sum(weights) - 1.0) < 1e-12


def test_pigorsch_reward_charges_entry_cost_only_on_entry() -> None:
    kwargs = {
        "asset_next_return": 0.03,
        "cross_section_next_returns": [0.01, -0.02, 0.03],
        "transaction_cost": 0.001,
    }
    assert abs(MODULE.invest_cash_reward(action=1, previous_action=0, **kwargs) - 0.029) < 1e-12
    assert abs(MODULE.invest_cash_reward(action=1, previous_action=1, **kwargs) - 0.03) < 1e-12


def test_multiscale_realized_variance_conserves_total_variance() -> None:
    returns = [0.01, -0.02, 0.015, -0.005, 0.012, -0.008, 0.004, -0.006]
    scales = MODULE.multiscale_realized_variance(returns, [1, 2, 4, 8])
    total = MODULE.realized_variance(returns)
    assert all(abs(sum(values) - total) < 1e-15 for values in scales.values())


def test_graph_relation_rows_are_normalized() -> None:
    identity = [[1.0, 0.0], [0.0, 1.0]]
    linked = [[1.0, 1.0], [1.0, 1.0]]
    adjacency = MODULE.combine_relations([identity, linked], [0.25, 0.75])
    assert all(abs(sum(row) - 1.0) < 1e-12 for row in adjacency)
