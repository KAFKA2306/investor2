from __future__ import annotations

import sys

import numpy as np
import pandas as pd
import pytest

from scripts.session_state_baseline import build_baseline, parse_args, select_prices, validate_snapshot_coverage


def _prices(rows: int = 160) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=rows)
    frames = []
    for ticker, offset in (("AAA", 0.0), ("BBB", 0.1)):
        close = 100.0 * np.exp(np.linspace(offset, offset + 0.25, rows))
        open_ = np.r_[close[0], close[:-1] * 1.001]
        frames.append(
            pd.DataFrame(
                {
                    "Ticker": ticker,
                    "Date": dates,
                    "Open": open_,
                    "High": np.maximum(open_, close),
                    "Low": np.minimum(open_, close),
                    "Close": close,
                    "AdjClose": close,
                    "Volume": 1000.0,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def test_cli_has_no_research_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["session_state_baseline.py"])
    with pytest.raises(SystemExit):
        parse_args()


def test_validate_snapshot_coverage_accepts_composed_intervals() -> None:
    manifests = [
        {"start": "2010-03-01", "end_exclusive": "2024-07-01"},
        {"start": "2024-07-01", "end_exclusive": "2026-03-15"},
    ]
    validate_snapshot_coverage(manifests, start="2022-04-01", end="2026-02-28")


def test_validate_snapshot_coverage_fails_on_gap() -> None:
    manifests = [
        {"start": "2019-01-01", "end_exclusive": "2024-05-01"},
        {"start": "2024-06-01", "end_exclusive": "2027-01-01"},
    ]
    with pytest.raises(AssertionError, match="gap"):
        validate_snapshot_coverage(manifests, start="2020-01-01", end="2026-12-31")


def test_validate_snapshot_coverage_fails_when_requested_end_exceeds_extensions() -> None:
    manifests = [
        {"start": "2022-01-01", "end_exclusive": "2026-01-01"},
    ]
    with pytest.raises(AssertionError, match="not fully covered"):
        validate_snapshot_coverage(manifests, start="2023-01-01", end="2026-08-21")


def test_select_prices_adjusted_mode_fails_closed_when_snapshot_lacks_adjusted_close() -> None:
    frame = _prices().drop(columns="AdjClose")
    with pytest.raises(AssertionError, match="AdjClose"):
        select_prices(
            frame,
            tickers=["AAA"],
            start="2025-01-01",
            end="2026-01-01",
            adjustment="adjusted",
        )


def test_select_prices_raw_mode_does_not_require_adjusted_close() -> None:
    frame = _prices().drop(columns="AdjClose")
    result = select_prices(
        frame,
        tickers=["AAA"],
        start="2025-01-01",
        end="2026-01-01",
        adjustment="raw",
    )
    assert set(result["Ticker"]) == {"AAA"}


def test_select_prices_fails_closed_when_ticker_missing() -> None:
    with pytest.raises(AssertionError, match="CCC"):
        select_prices(
            _prices(),
            tickers=["AAA", "CCC"],
            start="2025-01-01",
            end="2026-01-01",
            adjustment="adjusted",
        )


def test_build_baseline_records_exact_runtime_specification() -> None:
    payload = build_baseline(
        _prices(),
        tickers=["AAA", "BBB"],
        start="2025-01-02",
        end="2025-12-31",
        half_life=37,
        min_periods=23,
        trading_days=365,
        adjustment="raw",
    )
    assert payload["schema_version"] == "investor2.session-state-baseline.v3"
    assert payload["specification"]["session_tilt_half_life"] == 37
    assert payload["specification"]["session_tilt_min_periods"] == 23
    assert payload["specification"]["trading_days_per_year"] == 365
    assert payload["specification"]["adjustment"] == "raw"
    assert len(payload["results"]) == 2
    assert all(result["observations"] == 159 for result in payload["results"])
    assert all(result["latest_session_tilt"] is not None for result in payload["results"])
