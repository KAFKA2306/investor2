from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.alphazerobeta_prepare import build_asset_features, cross_sectional_zscore
from src.research.alpha_discovery_priority1 import (
    CandidateSpec,
    ast_fingerprint,
    build_candidate_pool,
    make_sparse_weight_path,
    materialize_candidate,
    returns_for_sparse_valuation,
    run_ablation,
    select_candidates,
    semantic_signature,
)

FEATURE_NAMES = [
    "log_return",
    "log_volume",
    "ret_mean_5",
    "ret_std_5",
    "momentum_5",
    "vol_mean_5",
    "vol_std_5",
    "ret_mean_20",
    "ret_std_20",
    "momentum_20",
    "vol_mean_20",
    "vol_std_20",
    "ret_mean_60",
    "ret_std_60",
    "momentum_60",
    "vol_mean_60",
    "vol_std_60",
]


def test_ast_fingerprint_is_sign_and_pair_order_invariant() -> None:
    positive = CandidateSpec("a", "single", "momentum_20", sign=1)
    negative = CandidateSpec("b", "single", "momentum_20", sign=-1)
    blend_ab = CandidateSpec("c", "blend", "momentum_20", "ret_std_20")
    blend_ba = CandidateSpec("d", "blend", "ret_std_20", "momentum_20")
    spread_ab = CandidateSpec("e", "spread", "momentum_20", "ret_std_20")
    spread_ba = CandidateSpec("f", "spread", "ret_std_20", "momentum_20")

    assert ast_fingerprint(positive) == ast_fingerprint(negative)
    assert ast_fingerprint(blend_ab) == ast_fingerprint(blend_ba)
    assert ast_fingerprint(spread_ab) == ast_fingerprint(spread_ba)
    assert ast_fingerprint(blend_ab) != ast_fingerprint(spread_ab)


def test_semantic_signature_collapses_same_economic_group_and_horizon() -> None:
    vol_mean = CandidateSpec("a", "single", "vol_mean_5")
    vol_std = CandidateSpec("b", "single", "vol_std_5")
    long_vol = CandidateSpec("c", "single", "vol_std_20")

    assert ast_fingerprint(vol_mean) != ast_fingerprint(vol_std)
    assert semantic_signature(vol_mean) == semantic_signature(vol_std)
    assert semantic_signature(vol_mean) != semantic_signature(long_vol)


def test_all_arms_receive_the_same_validation_budget() -> None:
    pool = build_candidate_pool(FEATURE_NAMES)
    baseline, baseline_scan = select_candidates(pool, arm="baseline", evaluator_budget=24)
    ast, ast_scan = select_candidates(pool, arm="ast_originality", evaluator_budget=24)
    semantic, semantic_scan = select_candidates(pool, arm="semantic_schema", evaluator_budget=24)

    assert len(baseline) == len(ast) == len(semantic) == 24
    assert len({ast_fingerprint(value) for value in baseline}) < 24
    assert len({ast_fingerprint(value) for value in ast}) == 24
    assert len({semantic_signature(value) for value in semantic}) == 24
    assert len(ast_scan) > len(baseline_scan)
    assert len(semantic_scan) > len(baseline_scan)


def test_materialize_candidate_preserves_expected_equivalences() -> None:
    left = np.arange(12, dtype=np.float64).reshape(3, 4)
    right = np.flip(left, axis=1)
    features = {"a": left, "b": right}

    blend_ab = materialize_candidate(CandidateSpec("a", "blend", "a", "b"), features)
    blend_ba = materialize_candidate(CandidateSpec("b", "blend", "b", "a"), features)
    spread_ab = materialize_candidate(CandidateSpec("c", "spread", "a", "b"), features)
    spread_ba = materialize_candidate(CandidateSpec("d", "spread", "b", "a"), features)

    np.testing.assert_allclose(blend_ab, blend_ba)
    np.testing.assert_allclose(spread_ab, -spread_ba)


def test_small_end_to_end_ablation_keeps_budgets_equal() -> None:
    rng = np.random.default_rng(7)
    t, n = 90, 8
    feature_names = ["log_return", "momentum_5", "ret_mean_5", "ret_std_5"]
    features = rng.normal(size=(t, n, len(feature_names)))
    returns = rng.normal(scale=0.01, size=(t, n))
    benchmark = rng.normal(scale=0.01, size=t)

    result = run_ablation(
        feature_names=feature_names,
        feature_tensor=features,
        returns=returns,
        benchmark=benchmark,
        train=(0, 40),
        validation=(40, 65),
        oos=(65, 90),
        evaluator_budget=6,
        finalists=2,
        n_long=2,
        n_short=2,
        transaction_cost_bps=1.0,
        borrow_fee_bps=1.0,
    )

    arms = dict(result["arms"])
    assert set(arms) == {"baseline", "ast_originality", "semantic_schema"}
    assert all(int(dict(payload)["validation_evaluator_calls"]) == 6 for payload in arms.values())
    assert all(int(dict(payload)["finalist_count"]) == 2 for payload in arms.values())
    assert result["winner_by_primary"]


def test_sparse_standardization_does_not_turn_missing_data_into_a_trade_signal() -> None:
    panel = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2026-01-05"] * 3),
            "Code": ["A", "B", "C"],
            "momentum_5": [1.0, 3.0, np.nan],
        }
    )
    sparse = cross_sectional_zscore(panel, ["momentum_5"], preserve_missing=True)
    dense = cross_sectional_zscore(panel, ["momentum_5"])
    assert np.isnan(sparse.loc[2, "momentum_5"])
    assert dense.loc[2, "momentum_5"] == 0.0
    np.testing.assert_allclose(sparse.loc[:1, "momentum_5"], [-1.0, 1.0])


def test_missing_trading_session_does_not_create_a_multiday_return() -> None:
    days = pd.to_datetime(["2026-01-05", "2026-01-06", "2026-01-07"])
    prices = pd.DataFrame({"Date": days, "Close": [100.0, np.nan, 120.0], "Volume": [100, np.nan, 100]})
    features = build_asset_features(prices)
    assert np.isnan(features.loc[days[2], "asset_return"])
    assert np.isnan(features.loc[days[2], "momentum_5"])


def test_sparse_positions_use_only_observed_decision_day_data() -> None:
    scores = np.tile([1.0, 2.0, 3.0, 4.0], (5, 1))
    observed = np.full((5, 4), 0.01)
    observed[1, 3] = np.nan
    first = make_sparse_weight_path(scores, observed, start=1, end=4, n_long=1, n_short=1, beta=1.0, gamma=0.0)
    changed_future = observed.copy()
    changed_future[2, 0] = 999.0
    second = make_sparse_weight_path(scores, changed_future, start=1, end=4, n_long=1, n_short=1, beta=1.0, gamma=0.0)
    np.testing.assert_array_equal(first[1], second[1])
    assert first[1, 3] == 0.0
    assert first[1, 2] > 0.0


def test_sparse_valuation_fails_closed_on_missing_held_asset() -> None:
    scores = np.tile([1.0, 2.0, 3.0, 4.0], (5, 1))
    observed = np.full((5, 4), 0.01)
    weights = make_sparse_weight_path(scores, observed, start=1, end=4, n_long=1, n_short=1, beta=1.0, gamma=0.0)
    observed[2, 3] = np.nan
    with pytest.raises(AssertionError, match="unpriced held asset"):
        returns_for_sparse_valuation(weights, observed, start=1, end=4)
    observed[2, 3] = 0.01
    observed[2, 1] = np.nan
    valued = returns_for_sparse_valuation(weights, observed, start=1, end=4)
    assert valued[2, 1] == 0.0
    assert np.isfinite(valued).all()
