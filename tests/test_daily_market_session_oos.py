from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.build_explicit_market_snapshot import explicit_universe, parse_tickers
from scripts.daily_market_session_oos import evaluate


def test_explicit_universe_is_exact_and_deduplicated() -> None:
    assert parse_tickers("spy, QQQ,MU") == ["SPY", "QQQ", "MU"]
    with pytest.raises(ValueError, match="duplicate"):
        parse_tickers("SPY,spy")
    universe = explicit_universe(region="US", tickers=["SPY", "MU"])
    assert universe.to_dict(orient="records") == [
        {"Ticker": "SPY", "Region": "us", "UniverseSource": "explicit"},
        {"Ticker": "MU", "Region": "us", "UniverseSource": "explicit"},
    ]


def _synthetic_prices() -> pd.DataFrame:
    dates = pd.bdate_range("2022-01-03", periods=760)
    tickers = ["SPY", "QQQ", "IWM", "DIA", "MU", "COST"]
    rows: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(tickers):
        previous_close = 100.0 + ticker_index
        for index, date in enumerate(dates):
            regime = 1.0 if (index // 90) % 2 == 0 else -1.0
            noise = 0.00015 * np.sin(index * 0.17 + ticker_index)
            overnight = 0.0025 * regime + noise
            intraday = -0.0018 * regime + 0.5 * noise
            open_price = previous_close * (1.0 + overnight)
            close_price = open_price * (1.0 + intraday)
            rows.append(
                {
                    "Ticker": ticker,
                    "Date": date,
                    "Open": open_price,
                    "Close": close_price,
                    "AdjClose": close_price,
                }
            )
            previous_close = close_price
    return pd.DataFrame(rows)


def test_oos_evaluation_uses_lagged_tilt_and_reports_direct_metrics() -> None:
    result = evaluate(
        _synthetic_prices(),
        tickers=["SPY", "QQQ", "IWM", "DIA", "MU", "COST"],
        start="2022-01-03",
        end="2024-11-29",
        train_start="2022-07-01",
        test_start="2024-01-02",
        adjustment="adjusted",
        half_life=40,
        min_periods=40,
        trading_days=252,
        costs_bps_per_side=[0.0, 1.0, 5.0],
        primary_cost_bps_per_side=1.0,
    )

    assert result["sample"]["train_rows"] > 100
    assert result["sample"]["test_rows"] > 100
    assert result["predictive"]["information_coefficient"] > 0
    assert result["predictive"]["mse_session_tilt"] < result["predictive"]["mse_intercept"]
    assert result["predictive"]["positive_ic_tickers"] == 6
    assert len(result["strategies"]) == 3
    assert result["strategies"][0]["session_tilt"]["max_drawdown"] <= 0
    assert result["specification"]["capacity_status"] == "NOT_TESTED_DAILY_BARS"
    assert result["decision_scope"].startswith("prelaunch daily-bar")


def test_primary_cost_must_be_in_sensitivity_grid() -> None:
    with pytest.raises(ValueError, match="primary cost"):
        evaluate(
            _synthetic_prices(),
            tickers=["SPY", "QQQ", "IWM", "DIA", "MU", "COST"],
            start="2022-01-03",
            end="2024-11-29",
            train_start="2022-07-01",
            test_start="2024-01-02",
            adjustment="adjusted",
            half_life=40,
            min_periods=40,
            trading_days=252,
            costs_bps_per_side=[0.0],
            primary_cost_bps_per_side=1.0,
        )
