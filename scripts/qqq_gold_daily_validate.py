#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from typing import cast

import pandas as pd

import scripts.alphazerobeta_empirical_run as market_source

START = "2020-07-31"
END = "2026-08-31"
EARLY_END = "2023-12-31"
RECENT_START = "2024-01-01"
COST_RATE = 20.0 / 10_000.0
TARGETS = {
    "QQQ": {"QQQ": 1.0, "GLD": 0.0, "SPY": 0.0},
    "QQQ80_GLD20": {"QQQ": 0.8, "GLD": 0.2, "SPY": 0.0},
    "QQQ80_SPY20": {"QQQ": 0.8, "GLD": 0.0, "SPY": 0.2},
}


@dataclass
class PathResult:
    dates: list[pd.Timestamp]
    returns: list[float]
    turnover: list[float]


def load_prices() -> tuple[pd.DataFrame, list[dict[str, object]]]:
    setattr(market_source, "SOURCE_START", START)
    setattr(market_source, "SOURCE_END", END)
    frames: list[pd.DataFrame] = []
    records: list[dict[str, object]] = []
    for symbol in ("QQQ", "GLD", "SPY"):
        frame, record = market_source.download_daily(symbol)
        part = frame[["Date", "Close"]].rename(columns={"Close": symbol})
        frames.append(part)
        records.append(record)

    prices = frames[0]
    for frame in frames[1:]:
        prices = prices.merge(frame, on="Date", how="inner", validate="one_to_one")
    prices = prices.sort_values("Date").reset_index(drop=True)

    counts = {str(record["symbol"]): cast(int, record["row_count"]) for record in records}
    if len(set(counts.values())) != 1:
        raise RuntimeError(f"symbol row counts differ before alignment: {counts}")
    if len(prices) != next(iter(counts.values())):
        raise RuntimeError(f"common-date alignment dropped rows: common={len(prices)}, raw={counts}")
    if prices.isna().any().any():
        raise RuntimeError("daily adjusted-close panel contains missing values")
    if (prices[["QQQ", "GLD", "SPY"]] <= 0).any().any():
        raise RuntimeError("daily adjusted-close panel contains non-positive values")
    return prices, records


def simulate(prices: pd.DataFrame, target: dict[str, float]) -> PathResult:
    symbols = ["QQQ", "GLD", "SPY"]
    sleeves = {symbol: float(target[symbol]) for symbol in symbols}
    dates = prices["Date"].tolist()
    returns: list[float] = []
    turnover_path: list[float] = []
    wealth = 1.0

    for idx in range(1, len(prices)):
        prev_wealth = wealth
        for symbol in symbols:
            gross = float(prices.loc[idx, symbol] / prices.loc[idx - 1, symbol])
            sleeves[symbol] *= gross
        pre_rebalance = sum(sleeves.values())
        if pre_rebalance <= 0:
            raise RuntimeError("portfolio wealth became non-positive")

        current_date = pd.Timestamp(prices.loc[idx, "Date"])
        is_month_end = (
            idx == len(prices) - 1
            or pd.Timestamp(prices.loc[idx + 1, "Date"]).month != current_date.month
        )
        one_way = 0.0
        if is_month_end and idx != len(prices) - 1:
            current_weights = {symbol: sleeves[symbol] / pre_rebalance for symbol in symbols}
            one_way = 0.5 * sum(
                abs(current_weights[symbol] - target[symbol]) for symbol in symbols
            )
            wealth = pre_rebalance * (1.0 - one_way * COST_RATE)
            sleeves = {symbol: wealth * target[symbol] for symbol in symbols}
        else:
            wealth = pre_rebalance

        returns.append(wealth / prev_wealth - 1.0)
        turnover_path.append(one_way)

    return PathResult(
        dates=[pd.Timestamp(value) for value in dates[1:]],
        returns=returns,
        turnover=turnover_path,
    )


def metrics(
    path: PathResult, start: str | None = None, end: str | None = None
) -> dict[str, float | int]:
    selected: list[tuple[pd.Timestamp, float, float]] = []
    for date, ret, turnover in zip(path.dates, path.returns, path.turnover, strict=True):
        if start is not None and date < pd.Timestamp(start):
            continue
        if end is not None and date > pd.Timestamp(end):
            continue
        selected.append((date, ret, turnover))
    if len(selected) < 2:
        raise RuntimeError(f"insufficient observations for period {start=} {end=}")

    rets = [item[1] for item in selected]
    wealth = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for ret in rets:
        wealth *= 1.0 + ret
        peak = max(peak, wealth)
        max_drawdown = min(max_drawdown, wealth / peak - 1.0)

    n = len(rets)
    tail_count = max(1, math.ceil(n * 0.05))
    tail = sorted(rets)[:tail_count]
    daily_std = statistics.stdev(rets)
    annualized_volatility = daily_std * math.sqrt(252.0)
    sharpe = statistics.mean(rets) / daily_std * math.sqrt(252.0) if daily_std > 0 else 0.0
    cagr = wealth ** (252.0 / n) - 1.0
    return {
        "observations": n,
        "cagr": cagr,
        "annualized_volatility": annualized_volatility,
        "sharpe": sharpe,
        "maximum_drawdown": max_drawdown,
        "daily_expected_shortfall_95": statistics.mean(tail),
        "worst_day": min(rets),
        "total_return": wealth - 1.0,
        "turnover": sum(item[2] for item in selected),
    }


def passes_period(results: dict[str, dict[str, float | int]]) -> bool:
    qqq = results["QQQ"]
    gold = results["QQQ80_GLD20"]
    spy = results["QQQ80_SPY20"]
    return bool(
        float(gold["maximum_drawdown"]) > float(qqq["maximum_drawdown"])
        and float(gold["maximum_drawdown"]) > float(spy["maximum_drawdown"])
        and float(gold["daily_expected_shortfall_95"])
        > float(qqq["daily_expected_shortfall_95"])
        and float(gold["daily_expected_shortfall_95"])
        > float(spy["daily_expected_shortfall_95"])
        and float(gold["annualized_volatility"]) < float(qqq["annualized_volatility"])
        and float(gold["annualized_volatility"]) < float(spy["annualized_volatility"])
        and float(gold["cagr"]) >= float(qqq["cagr"]) - 0.03
    )


def main() -> None:
    prices, records = load_prices()
    paths = {name: simulate(prices, target) for name, target in TARGETS.items()}
    periods = {
        "full_2020_08_to_2026_08": (None, None),
        "early_2020_08_to_2023_12": (None, EARLY_END),
        "recent_2024_01_to_2026_08": (RECENT_START, None),
    }
    results = {
        period: {name: metrics(path, start, end) for name, path in paths.items()}
        for period, (start, end) in periods.items()
    }
    early_pass = passes_period(results["early_2020_08_to_2023_12"])
    recent_pass = passes_period(results["recent_2024_01_to_2026_08"])
    verdict = "USE" if early_pass and recent_pass else "CONDITION"

    payload = {
        "schema_version": "investor2.portfolio-research-result.v1",
        "hypothesis": (
            "A fixed 20% gold sleeve in a QQQ-heavy portfolio reduces daily realized tail risk "
            "more reliably than replacing the same 20% with SPY, without sacrificing more than "
            "3 percentage points of CAGR."
        ),
        "verdict": verdict,
        "adoption_rule": {
            "required": [
                "Lower daily maximum drawdown than QQQ and QQQ80_SPY20 in both subperiods",
                "Lower 95% daily Expected Shortfall than both in both subperiods",
                "Lower annualized daily volatility than both in both subperiods",
                "CAGR no more than 3 percentage points below QQQ in either subperiod",
            ],
            "observed": "PASS" if verdict == "USE" else "FAIL",
            "period_pass": {"early": early_pass, "recent": recent_pass},
        },
        "data_contract": {
            "provider": "yahoo_chart",
            "provider_implementation": "scripts/alphazerobeta_empirical_run.py::download_daily",
            "frequency": "1Day",
            "price_field": "adjusted_close_when_available",
            "currency": "USD",
            "symbols": ["QQQ", "GLD", "SPY"],
            "source_period": {"start": START, "end": END},
            "common_rows": int(len(prices)),
            "source_records": records,
            "missing_data_policy": (
                "Fail on row-count disagreement, common-date drops, missing adjusted closes, or "
                "non-positive values. No interpolation or alternate-feed fallback."
            ),
        },
        "portfolio_contract": {
            "rebalancing": (
                "monthly fixed weights; rebalance after each month-end close for the next trading day"
            ),
            "transaction_cost_bps_per_one_way_turnover": 20,
            "initial_entry_cost": "excluded equally",
            "strategies": TARGETS,
            "risk_free_rate_for_sharpe": 0.0,
            "expected_shortfall": (
                "mean of the worst ceil(5% * observations) daily portfolio returns"
            ),
            "annualization": 252,
        },
        "results": results,
        "decision": {
            "use": (
                "Promote the 20% gold sleeve to USE only when both fixed subperiods pass all "
                "adoption criteria."
            ),
            "do_not_use": ["Do not use gold as an expected-return timing signal."],
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
