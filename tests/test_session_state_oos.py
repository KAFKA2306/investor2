from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.build_explicit_market_snapshot import explicit_universe, parse_tickers
from scripts.session_state_oos import evaluate


TICKERS = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"]


def test_explicit_universe_is_exact_and_deduplicated() -> None:
    assert parse_tickers("aaa, BBB,ccc") == ["AAA", "BBB", "CCC"]
    with pytest.raises(ValueError, match="duplicate"):
        parse_tickers("AAA,aaa")
    universe = explicit_universe(region="XX", tickers=["AAA", "CCC"])
    assert universe.to_dict(orient="records") == [
        {"Ticker": "AAA", "Region": "xx", "UniverseSource": "explicit"},
        {"Ticker": "CCC", "Region": "xx", "UniverseSource": "explicit"},
    ]


def _synthetic_prices() -> pd.DataFrame:
    dates = pd.bdate_range("2022-01-03", periods=760)
    rows: list[dict[str, object]] = []
    for ticker_index, ticker in enumerate(TICKERS):
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


def _evaluate(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "tickers": TICKERS,
        "benchmark_ticker": "CCC",
        "start": "2022-01-03",
        "end": "2024-11-29",
        "train_start": "2022-07-01",
        "test_start": "2024-01-02",
        "adjustment": "adjusted",
        "half_life": 40,
        "min_periods": 40,
        "trading_days": 252,
        "costs_bps_per_side": [0.0, 1.5, 7.0],
        "primary_cost_bps_per_side": 1.5,
        "stress_cost_bps_per_side": 7.0,
        "one_way_turnover_per_asset_day": 3.25,
        "minimum_ic": 0.0,
        "minimum_mse_improvement": 0.0,
        "minimum_positive_ic_tickers": 5,
        "minimum_primary_ann_return": -1.0,
        "minimum_primary_sharpe": -10.0,
        "minimum_stress_ann_return": -1.0,
        "minimum_stress_sharpe": -10.0,
    }
    kwargs.update(overrides)
    return evaluate(_synthetic_prices(), **kwargs)  # type: ignore[arg-type]


def test_oos_evaluation_uses_explicit_benchmark_cost_and_acceptance_contract() -> None:
    result = _evaluate()

    assert result["schema_version"] == "investor2.session-state-oos.v2"
    assert result["sample"]["train_rows"] > 100
    assert result["sample"]["test_rows"] > 100
    assert result["predictive"]["information_coefficient"] > 0
    assert result["predictive"]["mse_session_tilt"] < result["predictive"]["mse_intercept"]
    assert result["predictive"]["positive_ic_tickers"] == 6
    assert len(result["strategies"]) == 3
    assert result["strategies"][0]["session_tilt"]["max_drawdown"] <= 0
    assert result["strategies"][0]["one_way_turnover_per_asset_day"] == pytest.approx(3.25)
    assert "beta_to_benchmark_close_to_close" in result["strategies"][0]["session_tilt"]
    assert result["specification"]["benchmark_ticker"] == "CCC"
    assert result["specification"]["stress_cost_bps_per_side"] == pytest.approx(7.0)
    assert result["specification"]["minimum_positive_ic_tickers"] == 5
    assert result["decision_scope"] == "daily-bar SessionTilt under the supplied historical contract"
    assert "article_claim_audit" not in result


def test_primary_and_stress_costs_must_be_in_sensitivity_grid() -> None:
    with pytest.raises(ValueError, match="primary cost"):
        _evaluate(costs_bps_per_side=[0.0, 7.0])
    with pytest.raises(ValueError, match="stress cost"):
        _evaluate(costs_bps_per_side=[0.0, 1.5])


def test_benchmark_and_breadth_threshold_are_runtime_contracts() -> None:
    with pytest.raises(ValueError, match="benchmark_ticker"):
        _evaluate(benchmark_ticker="ZZZ")
    with pytest.raises(ValueError, match="minimum_positive_ic_tickers"):
        _evaluate(minimum_positive_ic_tickers=7)
