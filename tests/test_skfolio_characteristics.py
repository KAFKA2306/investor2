from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research.skfolio_characteristics import (
    SKFOLIO_VERSION,
    asset_panel_from_prices,
    asset_panel_from_prices_and_market_cap,
    build_market_cap_characteristics_model,
    build_price_only_characteristics_model,
    market_cap_model_contract,
    model_contract,
    require_pinned_skfolio,
)


def test_asset_panel_from_prices_uses_skfolio_simple_returns() -> None:
    prices = pd.DataFrame(
        {
            "A": [100.0, 110.0, 121.0],
            "B": [200.0, 180.0, 198.0],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )

    panel = asset_panel_from_prices(prices)

    np.testing.assert_allclose(
        panel["returns"],
        np.array(
            [
                [0.10, -0.10],
                [0.10, 0.10],
            ]
        ),
    )
    assert list(panel.asset_names) == ["A", "B"]
    assert panel.observations.tolist() == prices.index[1:].to_numpy().tolist()


def test_asset_panel_from_prices_requires_explicit_universe_for_missing_prices() -> None:
    prices = pd.DataFrame(
        {"A": [100.0, np.nan, 101.0], "B": [200.0, 201.0, 202.0]},
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )

    with pytest.raises(ValueError, match="active_mask is required"):
        asset_panel_from_prices(prices)


def test_estimation_mask_must_match_price_axes() -> None:
    prices = pd.DataFrame(
        {"A": [100.0, 101.0, 102.0], "B": [200.0, 201.0, 202.0]},
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )
    bad_mask = pd.DataFrame(
        True,
        index=prices.index,
        columns=["B", "A"],
    )

    with pytest.raises(ValueError, match="same index and columns"):
        asset_panel_from_prices(prices, estimation_mask=bad_mask)


def test_market_cap_panel_aligns_to_simple_return_dates() -> None:
    index = pd.date_range("2026-01-01", periods=3, freq="D")
    prices = pd.DataFrame({"A": [100.0, 101.0, 102.0], "B": [200.0, 202.0, 204.0]}, index=index)
    market_cap = pd.DataFrame(
        {"A": [1_000.0, 1_010.0, 1_020.0], "B": [2_000.0, 2_020.0, 2_040.0]},
        index=index,
    )

    panel = asset_panel_from_prices_and_market_cap(prices, market_cap)

    assert panel.observations.tolist() == index[1:].to_numpy().tolist()
    np.testing.assert_allclose(
        panel["market_cap"],
        market_cap.loc[index[1:]].to_numpy(dtype=float),
    )


def test_market_cap_panel_fails_closed_on_missing_or_nonpositive_values() -> None:
    index = pd.date_range("2026-01-01", periods=3, freq="D")
    prices = pd.DataFrame({"A": [100.0, 101.0, 102.0], "B": [200.0, 202.0, 204.0]}, index=index)
    market_cap = pd.DataFrame(
        {"A": [1_000.0, np.nan, 1_020.0], "B": [2_000.0, 2_020.0, 2_040.0]},
        index=index,
    )

    with pytest.raises(ValueError, match="finite and strictly positive"):
        asset_panel_from_prices_and_market_cap(prices, market_cap)

    market_cap.loc[index[1], "A"] = 0.0
    with pytest.raises(ValueError, match="finite and strictly positive"):
        asset_panel_from_prices_and_market_cap(prices, market_cap)


def test_price_only_model_contract_does_not_fake_market_cap() -> None:
    assert require_pinned_skfolio() == SKFOLIO_VERSION

    model = build_price_only_characteristics_model()
    contract = model_contract()

    assert model.benchmark_mcap_power == 0.0
    assert model.regression_mcap_power == 0.0
    assert model.exposure_lag == 1
    assert [name for name, _ in model.factors] == ["market", "momentum", "volatility"]
    assert contract["return_type"] == "simple"
    assert contract["market_cap_status"] == "not_required_equal_weighted"


def test_true_market_cap_candidate_uses_upstream_size_beta_and_weighting() -> None:
    model = build_market_cap_characteristics_model()
    contract = market_cap_model_contract()

    assert model.benchmark_mcap_power == 1.0
    assert model.regression_mcap_power == 0.5
    assert model.exposure_lag == 1
    assert [name for name, _ in model.factors] == ["market", "beta", "size"]
    assert contract["beta_descriptor"] == "skfolio.descriptor.EWMarketBeta"
    assert contract["size_descriptor"] == "skfolio.descriptor.LogMarketCap"
    assert contract["market_cap_status"] == "required_true_point_in_time_no_proxy_fallback"


def test_price_only_model_fits_with_explicit_investment_universe() -> None:
    n_observations = 260
    n_assets = 35
    time = np.arange(n_observations, dtype=float)
    prices: dict[str, np.ndarray] = {}
    for asset in range(n_assets):
        simple_returns = (
            0.0002
            + 0.003 * np.sin((time + asset * 0.7) / (8.0 + asset % 5))
            + 0.0015 * np.cos((time * (1.0 + asset / 100.0)) / 13.0)
        )
        prices[f"A{asset:02d}"] = 100.0 * np.cumprod(1.0 + simple_returns)

    price_frame = pd.DataFrame(
        prices,
        index=pd.date_range("2025-01-01", periods=n_observations, freq="B"),
    )
    panel = asset_panel_from_prices(price_frame)
    returns = pd.DataFrame(
        panel["returns"],
        index=pd.DatetimeIndex(panel.observations),
        columns=[str(name) for name in panel.asset_names],
    )
    model = build_price_only_characteristics_model()

    model.fit(X=returns, characteristics=panel)

    distribution = model.return_distribution_
    assert distribution.covariance.shape == (n_assets, n_assets)
    assert distribution.mu.shape == (n_assets,)
    assert np.isfinite(distribution.covariance).all()
    assert list(model.feature_names_in_) == list(returns.columns)
    assert list(model.factor_model_.asset_names) == list(returns.columns)
