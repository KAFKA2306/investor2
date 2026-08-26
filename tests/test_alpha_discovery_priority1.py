from __future__ import annotations

import numpy as np

from src.research.alpha_discovery_priority1 import (
    CandidateSpec,
    ast_fingerprint,
    build_candidate_pool,
    materialize_candidate,
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
