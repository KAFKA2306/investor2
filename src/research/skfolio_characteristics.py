"""Thin, auditable integration with skfolio's characteristics factor model."""

from __future__ import annotations

from importlib.metadata import version

import numpy as np
import pandas as pd
from skfolio.containers import AssetPanel
from skfolio.descriptor import EWMomentum, EWVolatility
from skfolio.factor_exposure import FixedWeightedFactor, GlobalFactor
from skfolio.preprocessing import prices_to_returns
from skfolio.prior import CharacteristicsFactorModel

SKFOLIO_VERSION = "1.0.0"
MOMENTUM_HALF_LIFE = 87.0
MOMENTUM_SKIP = 21
VOLATILITY_HALF_LIFE = 40.0
EXPOSURE_LAG = 1
MIN_REGRESSION_ASSETS = 30


def require_pinned_skfolio() -> str:
    """Fail closed when runtime skfolio differs from the reviewed implementation."""
    installed = version("skfolio")
    if installed != SKFOLIO_VERSION:
        raise RuntimeError(f"expected skfolio=={SKFOLIO_VERSION}, found {installed}")
    return installed


def _aligned_mask(
    mask: pd.DataFrame | None,
    *,
    prices: pd.DataFrame,
    returns: pd.DataFrame,
    name: str,
) -> np.ndarray | None:
    if mask is None:
        return None
    if not prices.index.equals(mask.index) or not prices.columns.equals(mask.columns):
        raise ValueError(f"{name} must have the same index and columns as prices")
    aligned = mask.loc[returns.index, returns.columns]
    if aligned.isna().any().any():
        raise ValueError(f"{name} contains missing values after return alignment")
    return aligned.to_numpy(dtype=bool, copy=True)


def asset_panel_from_prices(
    prices: pd.DataFrame,
    *,
    active_mask: pd.DataFrame | None = None,
    estimation_mask: pd.DataFrame | None = None,
) -> AssetPanel:
    """Build an AssetPanel using skfolio's canonical simple-return conversion.

    For a panel containing missing prices, callers must provide an explicit active mask.
    This avoids guessing whether a missing value means a holiday/data gap or that the
    security was outside the point-in-time universe.
    """
    require_pinned_skfolio()
    if prices.empty:
        raise ValueError("prices must not be empty")
    if not prices.index.is_unique:
        raise ValueError("prices index must be unique")
    if not prices.columns.is_unique:
        raise ValueError("prices columns must be unique")
    if len(prices.index) < 2:
        raise ValueError("prices must contain at least two observations")
    if prices.isna().any().any() and active_mask is None:
        raise ValueError("active_mask is required when prices contain missing values")

    returns = prices_to_returns(
        prices,
        log_returns=False,
        nan_threshold=1.0,
        drop_inceptions_nan=False,
        fill_nan=False,
    )
    if not isinstance(returns, pd.DataFrame):
        raise TypeError("skfolio prices_to_returns returned an unexpected value")
    if returns.empty:
        raise ValueError("no return observations remain after price conversion")

    active = _aligned_mask(active_mask, prices=prices, returns=returns, name="active_mask")
    estimation = _aligned_mask(
        estimation_mask,
        prices=prices,
        returns=returns,
        name="estimation_mask",
    )
    if active is None:
        active = np.ones(returns.shape, dtype=bool)
    if estimation is None:
        estimation = active.copy()

    return AssetPanel(
        fields={"returns": returns.to_numpy(dtype=float, copy=True)},
        observations=returns.index.to_numpy(copy=True),
        asset_names=[str(column) for column in returns.columns],
        active_mask=active,
        estimation_mask=estimation,
    )


def build_price_only_characteristics_model() -> CharacteristicsFactorModel:
    """Build the first PIT-safe model that needs no unavailable fundamental fields.

    Market-cap weighting is deliberately disabled until true point-in-time market
    capitalization is available. Price, volume, or dollar-volume proxies must not be
    substituted for market capitalization.
    """
    require_pinned_skfolio()
    return CharacteristicsFactorModel(
        factors=[
            ("market", GlobalFactor(family="market")),
            (
                "momentum",
                FixedWeightedFactor(
                    descriptors=[
                        (
                            "momentum",
                            EWMomentum(
                                half_life=MOMENTUM_HALF_LIFE,
                                skip=MOMENTUM_SKIP,
                            ),
                        )
                    ],
                    family="style",
                ),
            ),
            (
                "volatility",
                FixedWeightedFactor(
                    descriptors=[
                        (
                            "volatility",
                            EWVolatility(half_life=VOLATILITY_HALF_LIFE),
                        )
                    ],
                    family="style",
                ),
            ),
        ],
        exposure_lag=EXPOSURE_LAG,
        benchmark_mcap_power=0.0,
        regression_mcap_power=0.0,
        min_regression_assets=MIN_REGRESSION_ASSETS,
    )


def model_contract() -> dict[str, object]:
    """Return the reviewed model contract for manifests and result artifacts."""
    return {
        "engine": "skfolio.prior.CharacteristicsFactorModel",
        "skfolio_version": require_pinned_skfolio(),
        "return_type": "simple",
        "factors": ["market", "momentum", "volatility"],
        "momentum_half_life": MOMENTUM_HALF_LIFE,
        "momentum_skip": MOMENTUM_SKIP,
        "volatility_half_life": VOLATILITY_HALF_LIFE,
        "exposure_lag": EXPOSURE_LAG,
        "benchmark_mcap_power": 0.0,
        "regression_mcap_power": 0.0,
        "min_regression_assets": MIN_REGRESSION_ASSETS,
        "market_cap_status": "not_required_equal_weighted",
    }
