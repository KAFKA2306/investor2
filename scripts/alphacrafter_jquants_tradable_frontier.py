#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from scripts import alphacrafter_jquants_frontier as runner
from src.research.tradability import (
    mask_research_array,
    ranked_long_short_weights,
    resolve_tradable,
    tradability_summary,
)


def _argument_path(name: str) -> Path:
    try:
        index = sys.argv.index(name)
    except ValueError as exc:
        raise SystemExit(f"missing required argument {name}") from exc
    if index + 1 >= len(sys.argv):
        raise SystemExit(f"missing value for {name}")
    return Path(sys.argv[index + 1])


DATASET_PATH = _argument_path("--dataset")
OUTPUT_PATH = _argument_path("--output")
with np.load(DATASET_PATH, allow_pickle=False) as dataset:
    shape = dataset["returns"].shape
    TRADABLE = resolve_tradable(dataset, shape)

ORIENT = runner.orient_factor_on_train
FACTOR_METRICS = runner.factor_metrics
SCREEN = runner.screen_factors


def orient_factor_on_train(
    factor: np.ndarray,
    asset_returns: np.ndarray,
    train_start: int,
    train_end: int,
) -> tuple[np.ndarray, int]:
    return ORIENT(
        mask_research_array(factor, TRADABLE),
        mask_research_array(asset_returns, TRADABLE),
        train_start,
        train_end,
    )


def factor_metrics(
    factor: np.ndarray,
    asset_returns: np.ndarray,
    start: int,
    end: int,
    *,
    horizon: int,
):
    return FACTOR_METRICS(
        mask_research_array(factor, TRADABLE),
        mask_research_array(asset_returns, TRADABLE),
        start,
        end,
        horizon=horizon,
    )


def screen_factors(
    factors: dict[str, np.ndarray],
    asset_returns: np.ndarray,
    validation_start: int,
    validation_end: int,
):
    masked = {name: mask_research_array(values, TRADABLE) for name, values in factors.items()}
    return SCREEN(masked, mask_research_array(asset_returns, TRADABLE), validation_start, validation_end)


def make_weight_path(
    scores: np.ndarray,
    *,
    n_long: int,
    n_short: int,
    beta: float,
    gamma: float,
) -> np.ndarray:
    return ranked_long_short_weights(
        scores,
        TRADABLE,
        n_long=n_long,
        n_short=n_short,
        beta=beta,
        gamma=gamma,
    )


def main() -> None:
    runner.orient_factor_on_train = orient_factor_on_train
    runner.factor_metrics = factor_metrics
    runner.screen_factors = screen_factors
    runner.make_weight_path = make_weight_path
    runner.main()

    payload = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    payload["tradability"] = {
        **tradability_summary(TRADABLE),
        "research_rule": "inactive asset-days are excluded from factor IC/rank-IC observations",
        "trader_rule": "inactive assets are excluded before each long/short ranking and receive exactly zero weight",
    }
    substitutions = list(payload.get("substitutions", []))
    substitutions.append(
        "The cutoff-fixed 256-name universe is retained after cutoff; suspensions/delistings are represented by a daily tradability mask rather than future-survivor filtering."
    )
    payload["substitutions"] = substitutions
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
