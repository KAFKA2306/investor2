from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def normalize_daily_ohlc(frame: pd.DataFrame, *, require_adjusted_close: bool = True) -> pd.DataFrame:
    """Normalize daily OHLC and create corporate-action-adjusted open/close prices."""
    aliases = {"Code": "Ticker", "date": "Date", "Adj Close": "AdjClose"}
    data = frame.rename(
        columns={key: value for key, value in aliases.items() if key in frame.columns and value not in frame.columns}
    ).copy()
    required = {"Ticker", "Date", "Open", "Close"}
    missing = sorted(required - set(data.columns))
    if missing:
        raise AssertionError(f"daily OHLC input missing columns: {missing}")
    if require_adjusted_close and "AdjClose" not in data.columns:
        raise AssertionError("AdjClose is required for the primary corporate-action-adjusted specification")

    data["Ticker"] = data["Ticker"].astype(str)
    data["Date"] = pd.to_datetime(data["Date"], errors="raise").dt.tz_localize(None)
    for column in ("Open", "Close"):
        data[column] = pd.to_numeric(data[column], errors="raise")
    if "AdjClose" in data.columns:
        data["AdjClose"] = pd.to_numeric(data["AdjClose"], errors="raise")

    if data.duplicated(["Ticker", "Date"]).any():
        raise AssertionError("duplicate Ticker/Date rows")
    if (data[["Open", "Close"]] <= 0).any().any():
        raise AssertionError("Open and Close must be strictly positive")

    if "AdjClose" in data.columns:
        if (data["AdjClose"] <= 0).any():
            raise AssertionError("AdjClose must be strictly positive")
        factor = data["AdjClose"] / data["Close"]
    else:
        factor = pd.Series(1.0, index=data.index, dtype=float)

    data["AdjustmentFactor"] = factor
    data["AdjustedOpen"] = data["Open"] * factor
    data["AdjustedClose"] = data["Close"] * factor
    return data.sort_values(["Ticker", "Date"]).reset_index(drop=True)


def decompose_daily_sessions(frame: pd.DataFrame, *, require_adjusted_close: bool = True) -> pd.DataFrame:
    """Compute close->open, open->close, and close->close returns by ticker."""
    data = normalize_daily_ohlc(frame, require_adjusted_close=require_adjusted_close)
    previous_close = data.groupby("Ticker", observed=True)["AdjustedClose"].shift(1)
    out = data[["Ticker", "Date", "AdjustedOpen", "AdjustedClose", "AdjustmentFactor"]].copy()
    out["r_overnight"] = out["AdjustedOpen"] / previous_close - 1.0
    out["r_intraday"] = out["AdjustedClose"] / out["AdjustedOpen"] - 1.0
    out["r_close_to_close"] = out["AdjustedClose"] / previous_close - 1.0
    out["log_r_overnight"] = np.log(out["AdjustedOpen"] / previous_close)
    out["log_r_intraday"] = np.log(out["AdjustedClose"] / out["AdjustedOpen"])
    out["log_r_close_to_close"] = np.log(out["AdjustedClose"] / previous_close)
    valid = out["log_r_close_to_close"].notna()
    error = (
        out.loc[valid, "log_r_overnight"] + out.loc[valid, "log_r_intraday"] - out.loc[valid, "log_r_close_to_close"]
    ).abs()
    if not error.empty and float(error.max()) > 1e-12:
        raise AssertionError("log return decomposition identity failed")
    return out


def add_session_tilt(
    returns: pd.DataFrame,
    *,
    half_life: int = 126,
    min_periods: int | None = None,
) -> pd.DataFrame:
    """Add the preregistered point-in-time SessionTilt feature."""
    if half_life <= 0:
        raise ValueError("half_life must be positive")
    required = {
        "Ticker",
        "Date",
        "r_overnight",
        "r_intraday",
        "log_r_close_to_close",
    }
    missing = sorted(required - set(returns.columns))
    if missing:
        raise AssertionError(f"session return input missing columns: {missing}")
    minimum = half_life if min_periods is None else min_periods
    if minimum <= 1:
        raise ValueError("min_periods must be greater than 1")

    out = returns.sort_values(["Ticker", "Date"]).copy()
    out["session_spread"] = out["r_overnight"] - out["r_intraday"]
    spread_col = f"session_spread_ewma_{half_life}"
    vol_col = f"cc_vol_ewma_{half_life}"
    tilt_col = f"session_tilt_{half_life}"

    pieces: list[pd.DataFrame] = []
    for _, group in out.groupby("Ticker", observed=True, sort=False):
        item = group.copy()
        item[spread_col] = item["session_spread"].ewm(halflife=half_life, adjust=False, min_periods=minimum).mean()
        item[vol_col] = (
            item["log_r_close_to_close"].ewm(halflife=half_life, adjust=False, min_periods=minimum).std(bias=False)
        )
        item[tilt_col] = item[spread_col] / item[vol_col].replace(0.0, np.nan)
        pieces.append(item)
    return pd.concat(pieces, ignore_index=True)


def annualized_session_summary(
    returns: pd.DataFrame,
    *,
    trading_days: int = TRADING_DAYS_PER_YEAR,
) -> pd.DataFrame:
    """Summarize annualized overnight/intraday components under frozen conventions."""
    if trading_days <= 0:
        raise ValueError("trading_days must be positive")
    required = {
        "Ticker",
        "r_overnight",
        "r_intraday",
        "log_r_overnight",
        "log_r_intraday",
    }
    missing = sorted(required - set(returns.columns))
    if missing:
        raise AssertionError(f"session return input missing columns: {missing}")

    rows: list[dict[str, object]] = []
    for ticker, group in returns.groupby("Ticker", observed=True):
        valid = group.dropna(subset=["r_overnight", "r_intraday", "log_r_overnight", "log_r_intraday"])
        if valid.empty:
            continue
        rows.append(
            {
                "Ticker": str(ticker),
                "observations": int(len(valid)),
                "overnight_ann_arithmetic": float(valid["r_overnight"].mean() * trading_days),
                "intraday_ann_arithmetic": float(valid["r_intraday"].mean() * trading_days),
                "overnight_ann_log_compound": float(np.expm1(valid["log_r_overnight"].mean() * trading_days)),
                "intraday_ann_log_compound": float(np.expm1(valid["log_r_intraday"].mean() * trading_days)),
            }
        )
    return pd.DataFrame(rows).sort_values("Ticker").reset_index(drop=True)
