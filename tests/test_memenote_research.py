from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
MODULE_PATH = ROOT / "scripts" / "verify_memenote_research.py"
SPEC = importlib.util.spec_from_file_location("verify_memenote_research", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_frozen_price_snapshot_matches_manifest() -> None:
    manifest = json.loads(MODULE.PRICE_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert MODULE.sha256_file(MODULE.PRICE_PATH) == manifest["normalized_prices_sha256"]
    prices = MODULE.load_prices()
    assert list(prices.columns) == list(MODULE.CROSS_ASSET_UNIVERSE)
    assert prices.index.min().strftime("%Y-%m-%d") == "2020-01-02"
    assert prices.index.max().strftime("%Y-%m-%d") == "2024-12-31"


def test_log_relative_strength_is_sum_zero_and_ranking_equivalent() -> None:
    prices = MODULE.load_prices()
    centered = MODULE.centered_log_strength(prices, MODULE.PRIMARY_LOOKBACK).dropna(how="any")
    assert centered.sum(axis=1).abs().max() < 1e-12
    assert MODULE.ranking_agreement(prices, MODULE.PRIMARY_LOOKBACK) == pytest.approx(1.0)


def test_signal_uses_next_session_and_charges_turnover() -> None:
    prices = MODULE.load_prices()
    schedule = MODULE.target_schedule(prices, lookback=MODULE.PRIMARY_LOOKBACK, method="log")
    result = MODULE.simulate(prices, schedule, trading_cost_bps=MODULE.TRADING_COST_BPS)
    first_execution = min(schedule)
    assert result.loc[first_execution, "turnover"] == pytest.approx(1.0)
    assert result.loc[first_execution, "net_return"] < result.loc[first_execution, "gross_return"]


def test_funding_ablation_is_chronological_or_explicitly_blocked() -> None:
    result = MODULE.funding_ablation(MODULE.load_funding_frame())
    assert result["status"] in {"USE", "CONDITION", "REJECT", "BLOCKED"}
    if result["status"] != "BLOCKED":
        assert result["split_rows"]["train"] >= 10
        assert result["split_rows"]["validation"] >= 10
        assert result["split_rows"]["test"] >= 10
        assert "mse_improvement_fraction" in result["test"]


def test_report_preserves_negative_and_blocked_results() -> None:
    report = MODULE.build_report()
    results = report["hypothesis_results"]
    assert report["catalog_hypothesis_count"] == 4
    assert report["negative_results_are_preserved"] is True
    assert results["memenote_log_relative_strength_v1"]["incremental_log_transform_edge"] == "REJECT"
    assert results["memenote_log_relative_strength_v1"]["timing_signal"] == "BLOCKED"
    assert results["memenote_strategy_rule_reproduction_v1"]["status"] == "BLOCKED"
    assert set(results) == {
        "memenote_log_relative_strength_v1",
        "memenote_regime_parameter_dependence_v1",
        "memenote_btc_funding_incremental_v1",
        "memenote_strategy_rule_reproduction_v1",
    }
