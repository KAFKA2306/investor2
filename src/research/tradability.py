from __future__ import annotations

import numpy as np


def resolve_tradable(dataset: np.lib.npyio.NpzFile, shape: tuple[int, int]) -> np.ndarray:
    if "tradable" not in dataset.files:
        return np.ones(shape, dtype=bool)
    tradable = dataset["tradable"].astype(bool)
    if tradable.shape != shape:
        raise AssertionError(f"tradable mask {tradable.shape} != expected {shape}")
    return tradable


def mask_action_for_tradability(action: np.ndarray, tradable: np.ndarray) -> np.ndarray:
    values = np.asarray(action, dtype=np.float64).copy()
    active = np.asarray(tradable, dtype=bool)
    if values.ndim != 1 or active.shape != values.shape:
        raise ValueError("action and tradable must be same-shape 1-D arrays")
    active &= np.isfinite(values)
    if int(active.sum()) < 2:
        return np.zeros_like(values)
    active_mean = float(values[active].mean())
    values[~active] = active_mean
    return values


def mask_research_array(values: np.ndarray, tradable: np.ndarray) -> np.ndarray:
    out = np.asarray(values, dtype=np.float64).copy()
    active = np.asarray(tradable, dtype=bool)
    if out.shape != active.shape:
        raise ValueError("research array and tradable mask must have identical shape")
    out[~active] = np.nan
    return out


def ranked_long_short_weights(
    scores: np.ndarray,
    tradable: np.ndarray,
    *,
    n_long: int,
    n_short: int,
    beta: float,
    gamma: float,
) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    active = np.asarray(tradable, dtype=bool)
    if values.ndim != 2 or active.shape != values.shape:
        raise ValueError("scores and tradable must be same-shape [T,N] arrays")
    if n_long < 0 or n_short < 0 or n_long + n_short > values.shape[1]:
        raise ValueError("invalid long/short counts")
    weights = np.zeros_like(values)
    long_gross = beta * (1.0 + gamma) / 2.0
    short_gross = beta * (1.0 - gamma) / 2.0
    for t, row in enumerate(values):
        eligible = np.flatnonzero(active[t] & np.isfinite(row))
        if eligible.size < n_long + n_short:
            raise ValueError(
                f"only {eligible.size} tradable assets at row {t}; need {n_long + n_short} for frozen policy"
            )
        order = eligible[np.argsort(row[eligible], kind="mergesort")]
        if n_short:
            weights[t, order[:n_short]] = -short_gross / n_short
        if n_long:
            weights[t, order[-n_long:]] = long_gross / n_long
    return weights


def tradability_summary(tradable: np.ndarray) -> dict[str, int | float]:
    active = np.asarray(tradable, dtype=bool)
    if active.ndim != 2 or active.shape[0] == 0:
        raise ValueError("tradable must be a non-empty [T,N] array")
    counts = active.sum(axis=1)
    return {
        "min_active_assets": int(counts.min()),
        "median_active_assets": float(np.median(counts)),
        "max_active_assets": int(counts.max()),
        "incomplete_market_days": int(np.sum(counts < active.shape[1])),
        "inactive_asset_days": int(np.size(active) - active.sum()),
    }
