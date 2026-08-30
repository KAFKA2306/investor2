from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.skfolio_jquants_oos import build_walk_forward_folds, covariance_error_metrics, sha256_array


def test_build_walk_forward_folds_are_non_overlapping() -> None:
    folds = build_walk_forward_folds(
        pd.Timestamp("2026-02-01"),
        pd.Timestamp("2026-07-31"),
        train_months=12,
        fold_months=3,
    )

    assert len(folds) == 2
    assert folds[0].train_start == pd.Timestamp("2025-02-01")
    assert folds[0].train_end == pd.Timestamp("2026-01-31")
    assert folds[0].test_start == pd.Timestamp("2026-02-01")
    assert folds[0].test_end == pd.Timestamp("2026-04-30")
    assert folds[1].train_start == pd.Timestamp("2025-05-01")
    assert folds[1].test_start == pd.Timestamp("2026-05-01")
    assert folds[1].test_end == pd.Timestamp("2026-07-31")


def test_covariance_error_metrics_zero_for_exact_forecast() -> None:
    covariance = np.array([[0.04, 0.01], [0.01, 0.09]], dtype=float)

    metrics = covariance_error_metrics(covariance, covariance)

    assert metrics["frobenius_error"] == 0.0
    assert metrics["normalized_frobenius_error"] == 0.0
    assert metrics["diagonal_variance_mae"] == 0.0
    assert metrics["equal_weight_volatility_absolute_error"] == 0.0


def test_sha256_array_is_stable_and_shape_sensitive() -> None:
    array = np.array([[1.0, 2.0], [3.0, 4.0]])

    assert sha256_array(array) == sha256_array(array.copy())
    assert sha256_array(array) != sha256_array(array.reshape(1, 4))
