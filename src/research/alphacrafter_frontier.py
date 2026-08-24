from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class FactorMetrics:
    observations: int
    ic: float
    rank_ic: float
    icir: float
    rank_icir: float
    hit_ratio: float
    coverage: float
    turnover: float
    passed: bool


@dataclass(frozen=True)
class PortfolioMetrics:
    observations: int
    cumulative_return: float
    annualized_sharpe: float
    max_drawdown: float
    benchmark_correlation: float
    mean_turnover: float
    max_abs_net_exposure: float
    mean_gross_exposure: float


PAPER_THRESHOLDS = {
    1: {"ic": 0.015, "rank_ic": 0.015, "icir": 0.2, "rank_icir": 0.2},
    5: {"ic": 0.025, "rank_ic": 0.025, "icir": 0.25, "rank_icir": 0.25},
}
PAPER_MIN_COVERAGE = 0.9
PAPER_MAX_TURNOVER = 0.4
PAPER_HIT_DISTANCE = 0.1
PAPER_SCREENER_MIN_ABS_RANK_IC = 0.02


def _corr(x: np.ndarray, y: np.ndarray) -> float:
    left = np.asarray(x, dtype=np.float64)
    right = np.asarray(y, dtype=np.float64)
    if left.size < 2 or right.size != left.size:
        return 0.0
    if float(left.std(ddof=0)) <= 1e-12 or float(right.std(ddof=0)) <= 1e-12:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def _percentile_ranks(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    ranks[order] = np.arange(values.size, dtype=np.float64)
    if values.size <= 1:
        return np.zeros_like(ranks)
    return ranks / float(values.size - 1)


def _forward_returns(asset_returns: np.ndarray, horizon: int) -> np.ndarray:
    values = np.asarray(asset_returns, dtype=np.float64)
    if values.ndim != 2 or horizon < 1:
        raise ValueError("asset_returns must be [T,N] and horizon positive")
    out = np.full_like(values, np.nan, dtype=np.float64)
    for t in range(values.shape[0] - horizon):
        out[t] = values[t + 1 : t + 1 + horizon].sum(axis=0)
    return out


def daily_rank_ic(factor: np.ndarray, asset_returns: np.ndarray, horizon: int) -> np.ndarray:
    values = np.asarray(factor, dtype=np.float64)
    future = _forward_returns(asset_returns, horizon)
    if values.shape != future.shape:
        raise ValueError("factor and asset_returns must have same [T,N] shape")
    result = np.full(values.shape[0], np.nan, dtype=np.float64)
    for t in range(values.shape[0] - horizon):
        mask = np.isfinite(values[t]) & np.isfinite(future[t])
        if int(mask.sum()) < 2:
            continue
        result[t] = _corr(_percentile_ranks(values[t, mask]), _percentile_ranks(future[t, mask]))
    return result


def orient_factor_on_train(
    factor: np.ndarray, asset_returns: np.ndarray, train_start: int, train_end: int
) -> tuple[np.ndarray, int]:
    ranks = daily_rank_ic(factor, asset_returns, 1)
    effective_end = max(train_start, train_end - 1)
    observed = ranks[train_start:effective_end]
    score = float(np.nanmean(observed)) if observed.size else 0.0
    direction = 1 if score >= 0 else -1
    return np.asarray(factor, dtype=np.float64) * direction, direction


def factor_metrics(
    factor: np.ndarray,
    asset_returns: np.ndarray,
    start: int,
    end: int,
    *,
    horizon: int,
) -> FactorMetrics:
    values = np.asarray(factor, dtype=np.float64)
    future = _forward_returns(asset_returns, horizon)
    ic_series: list[float] = []
    rank_series: list[float] = []
    coverage_series: list[float] = []
    rank_paths: list[np.ndarray] = []
    effective_end = min(max(start, end - horizon), values.shape[0] - horizon)
    for t in range(start, effective_end):
        mask = np.isfinite(values[t]) & np.isfinite(future[t])
        coverage_series.append(float(mask.mean()))
        if int(mask.sum()) < 2:
            continue
        x = values[t, mask]
        y = future[t, mask]
        ic_series.append(_corr(x, y))
        rx = _percentile_ranks(x)
        ry = _percentile_ranks(y)
        rank_series.append(_corr(rx, ry))
        if bool(mask.all()):
            rank_paths.append(_percentile_ranks(values[t]))
    ic_arr = np.asarray(ic_series, dtype=np.float64)
    rank_arr = np.asarray(rank_series, dtype=np.float64)
    ic_mean = float(ic_arr.mean()) if ic_arr.size else 0.0
    rank_mean = float(rank_arr.mean()) if rank_arr.size else 0.0
    ic_std = float(ic_arr.std(ddof=0)) if ic_arr.size else 0.0
    rank_std = float(rank_arr.std(ddof=0)) if rank_arr.size else 0.0
    turnover_values = [
        float(np.abs(current - previous).mean()) for previous, current in zip(rank_paths, rank_paths[1:], strict=False)
    ]
    coverage = float(np.mean(coverage_series)) if coverage_series else 0.0
    hit_ratio = float(np.mean(rank_arr > 0)) if rank_arr.size else 0.0
    threshold = PAPER_THRESHOLDS[horizon]
    passed = (
        ic_mean > threshold["ic"]
        and rank_mean > threshold["rank_ic"]
        and (ic_mean / ic_std if ic_std > 1e-12 else 0.0) > threshold["icir"]
        and (rank_mean / rank_std if rank_std > 1e-12 else 0.0) > threshold["rank_icir"]
        and abs(hit_ratio - 0.5) > PAPER_HIT_DISTANCE
        and coverage > PAPER_MIN_COVERAGE
        and (float(np.mean(turnover_values)) if turnover_values else 0.0) < PAPER_MAX_TURNOVER
    )
    return FactorMetrics(
        observations=int(rank_arr.size),
        ic=ic_mean,
        rank_ic=rank_mean,
        icir=(ic_mean / ic_std if ic_std > 1e-12 else 0.0),
        rank_icir=(rank_mean / rank_std if rank_std > 1e-12 else 0.0),
        hit_ratio=hit_ratio,
        coverage=coverage,
        turnover=float(np.mean(turnover_values)) if turnover_values else 0.0,
        passed=bool(passed),
    )


def semantic_group(feature_name: str) -> str:
    name = feature_name.lower()
    if "momentum" in name:
        return "momentum"
    if "ret_mean" in name:
        return "return_mean"
    if "ret_std" in name:
        return "return_volatility"
    if "vol_mean" in name or "vol_std" in name or "log_volume" in name:
        return "volume"
    if "log_return" in name:
        return "short_return"
    return name.split("_", 1)[0]


def screen_factors(
    factors: dict[str, np.ndarray],
    asset_returns: np.ndarray,
    validation_start: int,
    validation_end: int,
) -> list[dict[str, float | str]]:
    candidates: list[dict[str, float | str]] = []
    for name, values in factors.items():
        ranks = daily_rank_ic(values, asset_returns, 1)
        effective_end = max(validation_start, validation_end - 1)
        observed = ranks[validation_start:effective_end]
        observed = observed[np.isfinite(observed)]
        recent = observed[-10:]
        suitability = float(recent.mean()) if recent.size else 0.0
        if abs(suitability) < PAPER_SCREENER_MIN_ABS_RANK_IC:
            continue
        candidates.append(
            {
                "feature": name,
                "semantic_group": semantic_group(name),
                "suitability_rank_ic_10d": suitability,
                "direction": 1.0 if suitability >= 0 else -1.0,
            }
        )
    best: dict[str, dict[str, float | str]] = {}
    for item in candidates:
        group = str(item["semantic_group"])
        current = best.get(group)
        if current is None or abs(float(item["suitability_rank_ic_10d"])) > abs(
            float(current["suitability_rank_ic_10d"])
        ):
            best[group] = item
    selected = sorted(best.values(), key=lambda item: abs(float(item["suitability_rank_ic_10d"])), reverse=True)
    denom = sum(abs(float(item["suitability_rank_ic_10d"])) for item in selected)
    for item in selected:
        item["weight"] = abs(float(item["suitability_rank_ic_10d"])) / denom if denom > 0 else 0.0
    return selected


def composite_scores(factors: dict[str, np.ndarray], selected: list[dict[str, float | str]]) -> np.ndarray:
    if not selected:
        first = next(iter(factors.values()))
        return np.zeros_like(first, dtype=np.float64)
    result = np.zeros_like(next(iter(factors.values())), dtype=np.float64)
    for item in selected:
        result += (
            float(item["weight"])
            * float(item["direction"])
            * np.asarray(factors[str(item["feature"])], dtype=np.float64)
        )
    return result


def make_weight_path(
    scores: np.ndarray,
    *,
    n_long: int,
    n_short: int,
    beta: float,
    gamma: float,
) -> np.ndarray:
    values = np.asarray(scores, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("scores must be [T,N]")
    if n_long < 0 or n_short < 0 or n_long + n_short > values.shape[1]:
        raise ValueError("invalid long/short counts")
    weights = np.zeros_like(values)
    long_gross = beta * (1.0 + gamma) / 2.0
    short_gross = beta * (1.0 - gamma) / 2.0
    for t, row in enumerate(values):
        order = np.argsort(row, kind="mergesort")
        if n_short:
            short_idx = order[:n_short]
            weights[t, short_idx] = -short_gross / n_short
        if n_long:
            long_idx = order[-n_long:]
            weights[t, long_idx] = long_gross / n_long
    return weights


def _annualized_sharpe(returns: np.ndarray) -> float:
    values = np.asarray(returns, dtype=np.float64)
    if values.size < 2:
        return 0.0
    std = float(values.std(ddof=1))
    return float(math.sqrt(252.0) * values.mean() / std) if std > 1e-12 else 0.0


def _max_drawdown(returns: np.ndarray) -> float:
    values = np.asarray(returns, dtype=np.float64)
    if values.size == 0:
        return 0.0
    equity = np.cumprod(1.0 + values)
    peak = np.maximum.accumulate(equity)
    return float((equity / peak - 1.0).min())


def evaluate_weights(
    weights: np.ndarray,
    asset_returns: np.ndarray,
    benchmark_returns: np.ndarray,
    start: int,
    end: int,
    *,
    transaction_cost_bps_per_side: float,
    borrow_fee_bps_per_year: float,
) -> tuple[PortfolioMetrics, np.ndarray]:
    w = np.asarray(weights, dtype=np.float64)
    r = np.asarray(asset_returns, dtype=np.float64)
    b = np.asarray(benchmark_returns, dtype=np.float64)
    if w.shape != r.shape:
        raise ValueError("weights and asset_returns must match")
    first = max(start, 0)
    last = min(end, w.shape[0])
    if last - first < 2:
        path = np.empty((0, w.shape[1]), dtype=np.float64)
        realized = np.empty((0, r.shape[1]), dtype=np.float64)
        benchmark = np.empty((0,), dtype=np.float64)
    else:
        # A weight formed at t realizes on t+1. The fold end is exclusive, so
        # never consume the first return outside the requested interval.
        path = w[first : last - 1]
        realized = r[first + 1 : last]
        benchmark = b[first + 1 : last]
    if path.shape != realized.shape:
        raise ValueError("misaligned realization path")
    previous = np.vstack([np.zeros((1, path.shape[1])), path[:-1]]) if path.size else path.copy()
    turnover = np.abs(path - previous).sum(axis=1) if path.size else np.empty((0,), dtype=np.float64)
    short_gross = np.abs(np.minimum(path, 0.0)).sum(axis=1) if path.size else np.empty((0,), dtype=np.float64)
    gross = np.abs(path).sum(axis=1) if path.size else np.empty((0,), dtype=np.float64)
    net = path.sum(axis=1) if path.size else np.empty((0,), dtype=np.float64)
    gross_return = np.einsum("tn,tn->t", path, realized) if path.size else np.empty((0,), dtype=np.float64)
    cost = turnover * transaction_cost_bps_per_side * 1e-4
    borrow = short_gross * borrow_fee_bps_per_year * 1e-4 / 252.0
    net_return = gross_return - cost - borrow
    metrics = PortfolioMetrics(
        observations=int(net_return.size),
        cumulative_return=float(np.prod(1.0 + net_return) - 1.0),
        annualized_sharpe=_annualized_sharpe(net_return),
        max_drawdown=_max_drawdown(net_return),
        benchmark_correlation=_corr(net_return, benchmark),
        mean_turnover=float(turnover.mean()) if turnover.size else 0.0,
        max_abs_net_exposure=float(np.abs(net).max()) if net.size else 0.0,
        mean_gross_exposure=float(gross.mean()) if gross.size else 0.0,
    )
    return metrics, net_return


def paper_strategy_gate(metrics: PortfolioMetrics) -> bool:
    return metrics.cumulative_return > 0.08 and metrics.annualized_sharpe > 0.6 and metrics.max_drawdown > -0.08


def as_dict(value: FactorMetrics | PortfolioMetrics) -> dict[str, object]:
    return asdict(value)
