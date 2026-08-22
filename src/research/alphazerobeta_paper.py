from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import pandas as pd

from src.research.alphazerobeta import make_walk_forward_folds

PaperMarket = Literal["us_large_cap", "uk_germany", "hong_kong", "china_proxy"]


@dataclass(frozen=True)
class PaperHyperparameters:
    hidden_size: int = 512
    head_hidden: int = 512
    agent_window: int = 100
    vol_corr_window: int = 60
    gamma: float = 0.99
    gae_lambda: float = 0.95
    ppo_clip: float = 0.20
    learning_rate: float = 3e-4
    entropy_coefficient: float = 0.01
    value_loss_coefficient: float = 0.5
    ppo_epochs: int = 10
    minibatch_trajectories: int = 256
    lambda_corr: float = 0.5
    lambda_turnover: float = 0.001
    train_months: int = 36
    validation_months: int = 6
    test_months: int = 6
    walk_forward_splits: int = 22
    restarts_per_fold: int = 9


@dataclass(frozen=True)
class ExecutionCost:
    top_decile_bps_per_side: float
    other_bps_per_side: float
    borrow_bps_per_year: float


PAPER_HYPERPARAMETERS = PaperHyperparameters()
PAPER_COSTS: dict[PaperMarket, ExecutionCost] = {
    "us_large_cap": ExecutionCost(5.0, 15.0, 30.0),
    "uk_germany": ExecutionCost(10.0, 15.0, 45.0),
    "hong_kong": ExecutionCost(10.0, 20.0, 75.0),
    "china_proxy": ExecutionCost(30.0, 30.0, 120.0),
}

REQUIRED_FEATURE_GROUPS = (
    "price_based",
    "volume_liquidity",
    "technical_indicators",
    "corporate_actions",
    "fundamentals",
    "earnings_surprises",
    "insider_trading",
    "sentiment",
    "governance",
    "macroeconomic",
    "rates_curves",
    "volatility_options",
    "cross_asset_indices",
    "sector_indices",
    "metadata",
)

TIME_VARYING_INDICES = ("GSPC", "NDX", "FTSE", "GDAXI", "HSI", "DJI")


def paper_fold_contract(dates: pd.DatetimeIndex) -> list[object]:
    folds = make_walk_forward_folds(
        dates,
        test_start="2014-01-01",
        test_end="2024-12-31",
        train_months=PAPER_HYPERPARAMETERS.train_months,
        validation_months=PAPER_HYPERPARAMETERS.validation_months,
        test_months=PAPER_HYPERPARAMETERS.test_months,
    )
    if len(folds) != PAPER_HYPERPARAMETERS.walk_forward_splits:
        raise AssertionError(f"paper protocol requires 22 folds, got {len(folds)}")
    return folds


def exact_paper_readiness(manifest: dict[str, object] | None) -> dict[str, object]:
    blockers: list[str] = []
    if manifest is None:
        blockers.append("missing exact-paper dataset manifest")
    else:
        source_start = str(manifest.get("source_start", ""))
        source_end = str(manifest.get("source_end", ""))
        if not source_start or pd.Timestamp(source_start) > pd.Timestamp("2004-01-01"):
            blockers.append("source history must start no later than 2004-01-01 for paper warm-up/features")
        if not source_end or pd.Timestamp(source_end) < pd.Timestamp("2024-12-31"):
            blockers.append("source history must include 2024-12-31")

        feature_groups = set(map(str, manifest.get("feature_groups", [])))
        missing_groups = sorted(set(REQUIRED_FEATURE_GROUPS) - feature_groups)
        if missing_groups:
            blockers.append("missing feature groups: " + ", ".join(missing_groups))

        membership = manifest.get("index_membership", {})
        membership_map = membership if isinstance(membership, dict) else {}
        bad_membership = [
            index for index in TIME_VARYING_INDICES if str(membership_map.get(index, "")) != "time-varying"
        ]
        if bad_membership:
            blockers.append("missing time-varying constituent history: " + ", ".join(bad_membership))

        providers = {str(value).lower() for value in manifest.get("providers", [])}
        if "bloomberg" not in providers:
            blockers.append("paper-result replication requires the licensed Bloomberg/vendor data contract")

    return {
        "mode": "exact-paper",
        "ready": not blockers,
        "blockers": blockers,
        "paper_hyperparameters": asdict(PAPER_HYPERPARAMETERS),
        "paper_cost_schedule": {key: asdict(value) for key, value in PAPER_COSTS.items()},
        "required_feature_groups": list(REQUIRED_FEATURE_GROUPS),
        "required_time_varying_indices": list(TIME_VARYING_INDICES),
        "evaluation_window": {"start": "2014-01-01", "end": "2024-12-31"},
        "paper_result_samples_per_market": (
            PAPER_HYPERPARAMETERS.walk_forward_splits * PAPER_HYPERPARAMETERS.restarts_per_fold
        ),
    }


def public_surrogate_deviations() -> list[str]:
    return [
        "uses the frozen public Yahoo ETF panel from the prior bounded validation, not licensed Bloomberg/FMP data",
        "uses 8 ETFs instead of a paper equity-index constituent universe",
        "uses 17 price/volume-derived features instead of the paper feature catalog",
        "covers only the two 2024 OOS folds available in the frozen panel instead of 22 folds over 2014-2024",
        "uses one fixed seed rather than nine independent RL initializations per fold",
        "charges the U.S. large-cap non-top-decile rate (15 bps/side) to every surrogate asset because the frozen model input does not retain the paper monthly ADV cost bucket",
        "uses Appendix-D-style 10 training iterations as an execution smoke; the paper does not disclose the total production update count/early-stopping budget needed to recreate Table 4",
    ]
