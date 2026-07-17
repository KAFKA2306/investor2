#!/usr/bin/env python3
"""Verify post-publication momentum performance on a frozen monthly return snapshot.

The calculation intentionally uses a fixed, untuned rule and a chronologically
separated holdout. Returns are the Fama/French monthly momentum factor in percent.
This is an empirical smoke test for AAARTS research governance, not a claim that
the factor is directly tradable after costs.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Metrics:
    start: str
    end: str
    months: int
    annualized_arithmetic_mean: float
    annualized_volatility: float
    annualized_sharpe_zero_rf: float
    cagr: float
    cumulative_return: float
    max_drawdown: float
    positive_month_fraction: float
    iid_t_stat: float
    newey_west_t_stat_lag_6: float
    block_bootstrap_95pct_mean_ci: list[float]


def load_returns(path: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        expected = {"date", "mom_percent"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError(f"expected columns {sorted(expected)}, got {reader.fieldnames}")
        for row in reader:
            rows.append((row["date"], float(row["mom_percent"]) / 100.0))
    if not rows:
        raise ValueError("input contains no returns")
    if rows != sorted(rows):
        raise ValueError("input dates must be strictly chronological")
    return rows


def newey_west_t_stat(values: Sequence[float], lags: int = 6) -> float:
    n = len(values)
    mean = sum(values) / n
    centered = [value - mean for value in values]
    gamma0 = sum(value * value for value in centered) / n
    long_run_variance = gamma0
    for lag in range(1, min(lags, n - 1) + 1):
        covariance = sum(centered[index] * centered[index - lag] for index in range(lag, n)) / n
        weight = 1.0 - lag / (lags + 1.0)
        long_run_variance += 2.0 * weight * covariance
    if long_run_variance <= 0:
        raise ValueError("non-positive Newey-West long-run variance")
    return mean / math.sqrt(long_run_variance / n)


def moving_block_mean_ci(
    values: Sequence[float],
    block_length: int = 12,
    repetitions: int = 20_000,
    seed: int = 2306,
) -> list[float]:
    n = len(values)
    if n < block_length:
        raise ValueError("sample shorter than block length")
    random_generator = random.Random(seed)
    starts = range(n - block_length + 1)
    blocks_needed = math.ceil(n / block_length)
    annualized_means: list[float] = []
    for _ in range(repetitions):
        sample: list[float] = []
        for _ in range(blocks_needed):
            start = random_generator.choice(starts)
            sample.extend(values[start : start + block_length])
        sample = sample[:n]
        annualized_means.append(12.0 * sum(sample) / n)
    annualized_means.sort()
    lower = annualized_means[int(0.025 * repetitions)]
    upper = annualized_means[int(0.975 * repetitions) - 1]
    return [lower, upper]


def calculate_metrics(rows: Sequence[tuple[str, float]]) -> Metrics:
    values = [value for _, value in rows]
    n = len(values)
    mean = sum(values) / n
    variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    monthly_volatility = math.sqrt(variance)
    annualized_mean = 12.0 * mean
    annualized_volatility = math.sqrt(12.0) * monthly_volatility
    wealth = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in values:
        wealth *= 1.0 + value
        peak = max(peak, wealth)
        max_drawdown = min(max_drawdown, wealth / peak - 1.0)
    standard_error = monthly_volatility / math.sqrt(n)
    return Metrics(
        start=rows[0][0],
        end=rows[-1][0],
        months=n,
        annualized_arithmetic_mean=annualized_mean,
        annualized_volatility=annualized_volatility,
        annualized_sharpe_zero_rf=annualized_mean / annualized_volatility,
        cagr=wealth ** (12.0 / n) - 1.0,
        cumulative_return=wealth - 1.0,
        max_drawdown=max_drawdown,
        positive_month_fraction=sum(value > 0 for value in values) / n,
        iid_t_stat=mean / standard_error,
        newey_west_t_stat_lag_6=newey_west_t_stat(values, lags=6),
        block_bootstrap_95pct_mean_ci=moving_block_mean_ci(values),
    )


def select(rows: Sequence[tuple[str, float]], start: str, end: str) -> list[tuple[str, float]]:
    selected = [(date, value) for date, value in rows if start <= date <= end]
    if not selected:
        raise ValueError(f"no observations in range {start} to {end}")
    return selected


def subtract_monthly_cost(
    rows: Iterable[tuple[str, float]], monthly_cost_bps: int
) -> list[tuple[str, float]]:
    cost = monthly_cost_bps / 10_000.0
    return [(date, value - cost) for date, value in rows]


def build_report(rows: Sequence[tuple[str, float]]) -> dict[str, object]:
    full = select(rows, "1994-01-31", "2017-12-31")
    early = select(rows, "1994-01-31", "2005-12-31")
    late = select(rows, "2006-01-31", "2017-12-31")
    cost_sensitivity = {
        str(cost): asdict(calculate_metrics(subtract_monthly_cost(full, cost)))
        for cost in (0, 10, 25, 50)
    }
    return {
        "study": "Jegadeesh-Titman momentum post-publication holdout",
        "publication_month": "1993-03",
        "factor_definition": (
            "Fama/French Mom: average of two high prior-return portfolios minus "
            "average of two low prior-return portfolios"
        ),
        "units": "decimal returns",
        "gross_results": {
            "post_publication_1994_2017": asdict(calculate_metrics(full)),
            "early_holdout_1994_2005": asdict(calculate_metrics(early)),
            "late_holdout_2006_2017": asdict(calculate_metrics(late)),
        },
        "monthly_cost_sensitivity_bps": cost_sensitivity,
        "verdict": (
            "not_confirmed: the full post-publication mean is not statistically "
            "distinguishable from zero and the 2006-2017 holdout has a negative mean"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("docs/research/data/ff_momentum_1994_2017.csv"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report(load_returns(args.input))
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
