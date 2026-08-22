from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn

PAPER_LAMBDA_CORR = 0.5
PAPER_LAMBDA_TURNOVER = 0.001
PAPER_VOL_WINDOW = 60
PAPER_AGENT_WINDOW = 100
PAPER_GAMMA = 0.99
PAPER_GAE_LAMBDA = 0.95
PAPER_PPO_CLIP = 0.20
PAPER_PPO_EPOCHS = 10
PAPER_LEARNING_RATE = 3e-4


@dataclass(frozen=True)
class WalkForwardFold:
    index: int
    train_start: str
    train_end: str
    validation_start: str
    validation_end: str
    test_start: str
    test_end: str
    train_indices: tuple[int, int]
    validation_indices: tuple[int, int]
    test_indices: tuple[int, int]


@dataclass(frozen=True)
class EvaluationMetrics:
    observations: int
    annualized_sharpe: float
    benchmark_correlation: float
    max_drawdown: float
    cumulative_return: float
    mean_turnover: float
    max_abs_net_exposure: float
    mean_gross_exposure: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def project_market_neutral(weights: np.ndarray) -> np.ndarray:
    values = np.asarray(weights, dtype=np.float64)
    if values.ndim != 1:
        raise ValueError("weights must be a 1-D vector")
    centered = values - values.mean()
    gross = float(np.abs(centered).sum())
    if gross > 1.0:
        centered = centered / gross
    return centered.astype(np.float32)


def project_market_neutral_torch(weights: torch.Tensor) -> torch.Tensor:
    centered = weights - weights.mean(dim=-1, keepdim=True)
    gross = centered.abs().sum(dim=-1, keepdim=True)
    scale = torch.clamp(gross, min=1.0)
    return centered / scale


def rolling_corr(portfolio_history: np.ndarray, benchmark_history: np.ndarray) -> float:
    portfolio = np.asarray(portfolio_history, dtype=np.float64)
    benchmark = np.asarray(benchmark_history, dtype=np.float64)
    if portfolio.shape != benchmark.shape:
        raise ValueError("portfolio and benchmark histories must have identical shapes")
    if portfolio.size < 2 or float(portfolio.std(ddof=0)) <= 1e-12 or float(benchmark.std(ddof=0)) <= 1e-12:
        return 0.0
    return float(np.corrcoef(portfolio, benchmark)[0, 1])


def alpha_zero_beta_reward(
    rp_t: float,
    rm_t: float,
    portfolio_history: np.ndarray,
    benchmark_history: np.ndarray,
    weights: np.ndarray,
    previous_weights: np.ndarray,
    *,
    lambda_corr: float = PAPER_LAMBDA_CORR,
    lambda_turnover: float = PAPER_LAMBDA_TURNOVER,
) -> float:
    portfolio = np.asarray(portfolio_history, dtype=np.float64)
    sigma = max(float(portfolio.std(ddof=0)) if portfolio.size else 0.0, 1e-8)
    corr = rolling_corr(portfolio, np.asarray(benchmark_history, dtype=np.float64))
    turnover = float(np.abs(np.asarray(weights) - np.asarray(previous_weights)).sum())
    return float((rp_t - rm_t) / sigma - lambda_corr * corr - lambda_turnover * turnover)


def _index_bounds(dates: pd.DatetimeIndex, start: pd.Timestamp, end_exclusive: pd.Timestamp) -> tuple[int, int]:
    left = int(dates.searchsorted(start, side="left"))
    right = int(dates.searchsorted(end_exclusive, side="left"))
    if right <= left:
        raise ValueError(f"empty interval: {start.date()} to {end_exclusive.date()}")
    return left, right


def make_walk_forward_folds(
    dates: Iterable[str | np.datetime64 | pd.Timestamp],
    *,
    test_start: str,
    test_end: str,
    train_months: int = 36,
    validation_months: int = 6,
    test_months: int = 6,
) -> list[WalkForwardFold]:
    idx = pd.DatetimeIndex(pd.to_datetime(list(dates))).sort_values()
    if idx.empty or idx.has_duplicates:
        raise ValueError("dates must be non-empty and unique")
    test_cursor = pd.Timestamp(test_start)
    final_exclusive = pd.Timestamp(test_end) + pd.Timedelta(days=1)
    folds: list[WalkForwardFold] = []
    fold_index = 0
    while test_cursor < final_exclusive:
        test_exclusive = min(test_cursor + pd.DateOffset(months=test_months), final_exclusive)
        validation_start = test_cursor - pd.DateOffset(months=validation_months)
        train_start = validation_start - pd.DateOffset(months=train_months)
        if train_start < idx[0]:
            raise ValueError(
                f"insufficient history for fold {fold_index}: need {train_start.date()}, have {idx[0].date()}"
            )
        train = _index_bounds(idx, train_start, validation_start)
        validation = _index_bounds(idx, validation_start, test_cursor)
        test = _index_bounds(idx, test_cursor, test_exclusive)
        folds.append(
            WalkForwardFold(
                index=fold_index,
                train_start=str(idx[train[0]].date()),
                train_end=str(idx[train[1] - 1].date()),
                validation_start=str(idx[validation[0]].date()),
                validation_end=str(idx[validation[1] - 1].date()),
                test_start=str(idx[test[0]].date()),
                test_end=str(idx[test[1] - 1].date()),
                train_indices=train,
                validation_indices=validation,
                test_indices=test,
            )
        )
        fold_index += 1
        test_cursor = test_exclusive
    return folds


def _safe_annualized_sharpe(returns: np.ndarray) -> float:
    values = np.asarray(returns, dtype=np.float64)
    if values.size < 2:
        return 0.0
    std = float(values.std(ddof=1))
    if std <= 1e-12:
        return 0.0
    return float(math.sqrt(252.0) * values.mean() / std)


def _max_drawdown(returns: np.ndarray) -> float:
    equity = np.cumprod(1.0 + np.asarray(returns, dtype=np.float64))
    if equity.size == 0:
        return 0.0
    peaks = np.maximum.accumulate(equity)
    drawdowns = equity / peaks - 1.0
    return float(drawdowns.min())


def evaluate_weight_path(
    weights: np.ndarray,
    asset_returns: np.ndarray,
    benchmark_returns: np.ndarray,
    *,
    transaction_cost_bps_per_side: float = 15.0,
    borrow_fee_bps_per_year: float = 100.0,
) -> tuple[EvaluationMetrics, np.ndarray]:
    w = np.asarray(weights, dtype=np.float64)
    returns = np.asarray(asset_returns, dtype=np.float64)
    benchmark = np.asarray(benchmark_returns, dtype=np.float64)
    if w.ndim != 2 or returns.ndim != 2 or w.shape != returns.shape:
        raise ValueError("weights and asset_returns must be same-shape [T, N] arrays")
    if benchmark.shape != (w.shape[0],):
        raise ValueError("benchmark_returns must have shape [T]")
    projected = np.stack([project_market_neutral(row) for row in w]).astype(np.float64)
    previous = np.vstack([np.zeros((1, projected.shape[1])), projected[:-1]])
    turnover = np.abs(projected - previous).sum(axis=1)
    gross = np.abs(projected).sum(axis=1)
    net_exposure = projected.sum(axis=1)
    short_gross = np.abs(np.minimum(projected, 0.0)).sum(axis=1)
    gross_return = np.einsum("tn,tn->t", projected, returns)
    trading_cost = turnover * transaction_cost_bps_per_side * 1e-4
    borrow_cost = short_gross * borrow_fee_bps_per_year * 1e-4 / 252.0
    net_return = gross_return - trading_cost - borrow_cost
    corr = rolling_corr(net_return, benchmark)
    metrics = EvaluationMetrics(
        observations=int(net_return.size),
        annualized_sharpe=_safe_annualized_sharpe(net_return),
        benchmark_correlation=corr,
        max_drawdown=_max_drawdown(net_return),
        cumulative_return=float(np.prod(1.0 + net_return) - 1.0),
        mean_turnover=float(turnover.mean()) if turnover.size else 0.0,
        max_abs_net_exposure=float(np.abs(net_exposure).max()) if net_exposure.size else 0.0,
        mean_gross_exposure=float(gross.mean()) if gross.size else 0.0,
    )
    return metrics, net_return


class AlphaZeroBetaEnvironment:
    def __init__(
        self,
        asset_returns: np.ndarray,
        benchmark_returns: np.ndarray,
        *,
        start: int,
        end: int,
        lambda_corr: float = PAPER_LAMBDA_CORR,
        lambda_turnover: float = PAPER_LAMBDA_TURNOVER,
        vol_window: int = PAPER_VOL_WINDOW,
    ) -> None:
        self.asset_returns = np.asarray(asset_returns, dtype=np.float32)
        self.benchmark_returns = np.asarray(benchmark_returns, dtype=np.float32)
        if self.asset_returns.ndim != 2:
            raise ValueError("asset_returns must be [T, N]")
        if self.benchmark_returns.shape != (self.asset_returns.shape[0],):
            raise ValueError("benchmark_returns length mismatch")
        if start < 0 or end > self.asset_returns.shape[0] - 1 or end <= start:
            raise ValueError("invalid environment bounds")
        self.start = start
        self.end = end
        self.n_assets = self.asset_returns.shape[1]
        self.lambda_corr = lambda_corr
        self.lambda_turnover = lambda_turnover
        self.vol_window = vol_window
        self.reset()

    def reset(self) -> int:
        self.t = self.start
        self.previous_weights = np.zeros(self.n_assets, dtype=np.float32)
        self.portfolio_history: list[float] = []
        self.benchmark_history: list[float] = []
        return self.t

    def step(self, action: np.ndarray) -> tuple[int, float, bool, dict[str, float]]:
        weights = project_market_neutral(action)
        rp_t = float(weights @ self.asset_returns[self.t + 1])
        rm_t = float(self.benchmark_returns[self.t + 1])
        s = max(0, len(self.portfolio_history) - self.vol_window)
        reward = alpha_zero_beta_reward(
            rp_t,
            rm_t,
            np.asarray(self.portfolio_history[s:], dtype=np.float64),
            np.asarray(self.benchmark_history[s:], dtype=np.float64),
            weights,
            self.previous_weights,
            lambda_corr=self.lambda_corr,
            lambda_turnover=self.lambda_turnover,
        )
        turnover = float(np.abs(weights - self.previous_weights).sum())
        self.portfolio_history.append(rp_t)
        self.benchmark_history.append(rm_t)
        self.previous_weights = weights
        self.t += 1
        done = self.t >= self.end - 1
        return self.t, reward, done, {"portfolio_return": rp_t, "benchmark_return": rm_t, "turnover": turnover}


class MultiScaleEncoder(nn.Module):
    def __init__(self, feature_dim: int, hidden_size: int = 512, agent_window: int = PAPER_AGENT_WINDOW) -> None:
        super().__init__()
        if feature_dim <= 0 or agent_window < 35:
            raise ValueError("feature_dim must be positive and agent_window must be at least 35")
        channels = 3 * feature_dim
        layers: list[nn.Module] = []
        previous = channels
        for out_channels, kernel, stride in zip((32, 64, 64), (8, 4, 3), (4, 2, 1), strict=True):
            layers.extend([nn.Conv1d(previous, out_channels, kernel_size=kernel, stride=stride), nn.ReLU(inplace=True)])
            previous = out_channels
        self.conv = nn.Sequential(*layers, nn.Flatten())
        with torch.no_grad():
            flat_dim = int(self.conv(torch.zeros(1, channels, agent_window)).numel())
        self.gru = nn.GRU(flat_dim, hidden_size, batch_first=True)

    def forward(
        self,
        daily: torch.Tensor,
        weekly: torch.Tensor,
        monthly: torch.Tensor,
        hidden: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        features = self.conv(torch.cat([daily, weekly, monthly], dim=1)).unsqueeze(1)
        out, next_hidden = self.gru(features, hidden)
        return out.squeeze(1), next_hidden


class PolicyValueNet(nn.Module):
    def __init__(
        self,
        feature_dim: int,
        num_assets: int,
        *,
        hidden_size: int = 512,
        head_hidden: int = 512,
        agent_window: int = PAPER_AGENT_WINDOW,
    ) -> None:
        super().__init__()
        self.encoder = MultiScaleEncoder(feature_dim, hidden_size=hidden_size, agent_window=agent_window)
        self.policy_head = nn.Sequential(
            nn.Linear(hidden_size, head_hidden),
            nn.ReLU(inplace=True),
            nn.Linear(head_hidden, num_assets),
            nn.Tanh(),
        )
        self.value_head = nn.Sequential(
            nn.Linear(hidden_size, head_hidden), nn.ReLU(inplace=True), nn.Linear(head_hidden, 1)
        )

    def forward(
        self,
        daily: torch.Tensor,
        weekly: torch.Tensor,
        monthly: torch.Tensor,
        hidden: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        embedding, next_hidden = self.encoder(daily, weekly, monthly, hidden)
        return self.policy_head(embedding), self.value_head(embedding).squeeze(-1), next_hidden


def multiscale_window(
    features: np.ndarray,
    t: int,
    *,
    agent_window: int = PAPER_AGENT_WINDOW,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(features, dtype=np.float32)
    if values.ndim != 3:
        raise ValueError("features must be [T, N, F]")
    feature_dim = values.shape[1] * values.shape[2]

    def sample(step: int) -> np.ndarray:
        indices = np.arange(t - (agent_window - 1) * step, t + 1, step)
        indices = np.clip(indices, 0, values.shape[0] - 1)
        return values[indices].reshape(agent_window, feature_dim).T

    return sample(1), sample(5), sample(21)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def metrics_to_dict(metrics: EvaluationMetrics) -> dict[str, float | int]:
    return asdict(metrics)
