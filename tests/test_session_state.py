from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.research.session_state import (
    add_session_tilt,
    annualized_session_summary,
    decompose_daily_sessions,
    normalize_daily_ohlc,
)


def _frame(rows: int = 160) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=rows)
    close = 100.0 * np.exp(np.linspace(0.0, 0.25, rows))
    open_ = np.r_[100.0, close[:-1] * 1.001]
    return pd.DataFrame(
        {
            "Ticker": ["AAA"] * rows,
            "Date": dates,
            "Open": open_,
            "Close": close,
            "AdjClose": close,
        }
    )


def test_decomposition_matches_definitions_and_log_identity() -> None:
    frame = pd.DataFrame(
        {
            "Ticker": ["AAA", "AAA"],
            "Date": ["2026-01-02", "2026-01-05"],
            "Open": [100.0, 110.0],
            "Close": [105.0, 120.0],
            "AdjClose": [100.0, 120.0],
        }
    )
    result = decompose_daily_sessions(frame, adjustment="adjusted")
    second = result.iloc[1]
    assert second["r_overnight"] == pytest.approx(0.10)
    assert second["r_intraday"] == pytest.approx(120.0 / 110.0 - 1.0)
    assert second["log_r_overnight"] + second["log_r_intraday"] == pytest.approx(second["log_r_close_to_close"])


def test_adjusted_mode_removes_split_discontinuity() -> None:
    frame = pd.DataFrame(
        {
            "Ticker": ["AAA", "AAA"],
            "Date": ["2026-01-02", "2026-01-05"],
            "Open": [100.0, 50.0],
            "Close": [100.0, 50.0],
            "AdjClose": [50.0, 50.0],
        }
    )
    result = decompose_daily_sessions(frame, adjustment="adjusted")
    assert result.iloc[1]["r_overnight"] == pytest.approx(0.0)
    assert result.iloc[1]["r_close_to_close"] == pytest.approx(0.0)


def test_raw_mode_preserves_raw_split_discontinuity() -> None:
    frame = pd.DataFrame(
        {
            "Ticker": ["AAA", "AAA"],
            "Date": ["2026-01-02", "2026-01-05"],
            "Open": [100.0, 50.0],
            "Close": [100.0, 50.0],
        }
    )
    result = decompose_daily_sessions(frame, adjustment="raw")
    assert result.iloc[1]["r_overnight"] == pytest.approx(-0.5)


def test_adjusted_mode_requires_adjusted_close() -> None:
    frame = pd.DataFrame(
        {
            "Ticker": ["AAA"],
            "Date": ["2026-01-02"],
            "Open": [10.0],
            "Close": [11.0],
        }
    )
    with pytest.raises(AssertionError, match="AdjClose"):
        normalize_daily_ohlc(frame, adjustment="adjusted")


def test_session_tilt_has_no_future_lookahead() -> None:
    frame = _frame()
    base = add_session_tilt(
        decompose_daily_sessions(frame, adjustment="adjusted"),
        half_life=20,
        min_periods=17,
    )
    altered_frame = frame.copy()
    altered_frame.loc[altered_frame.index[-1], ["Open", "Close", "AdjClose"]] = [
        500.0,
        600.0,
        600.0,
    ]
    altered = add_session_tilt(
        decompose_daily_sessions(altered_frame, adjustment="adjusted"),
        half_life=20,
        min_periods=17,
    )
    column = "session_tilt_20"
    pd.testing.assert_series_equal(
        base.iloc[:-1][column].reset_index(drop=True),
        altered.iloc[:-1][column].reset_index(drop=True),
        check_names=False,
    )


def test_session_tilt_uses_explicit_half_life_and_warmup() -> None:
    result = add_session_tilt(
        decompose_daily_sessions(_frame(80), adjustment="adjusted"),
        half_life=37,
        min_periods=23,
    )
    assert "session_tilt_37" in result.columns
    assert pd.isna(result["session_tilt_37"].iloc[22])
    assert np.isfinite(result["session_tilt_37"].iloc[-1])


def test_annualized_summary_uses_explicit_trading_days() -> None:
    returns = decompose_daily_sessions(_frame(20), adjustment="adjusted")
    summary = annualized_session_summary(returns, trading_days=365)
    expected = returns["r_overnight"].dropna().mean() * 365
    assert summary.iloc[0]["overnight_ann_arithmetic"] == pytest.approx(expected)
