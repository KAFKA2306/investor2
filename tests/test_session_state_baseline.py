from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.session_state_baseline import build_baseline, select_prices, validate_snapshot_coverage


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


def test_validate_snapshot_coverage_accepts_base_plus_year_extension() -> None:
    manifests = [
        {"start": "2004-01-01", "end_exclusive": "2025-01-01"},
        {"start": "2025-01-01", "end_exclusive": "2026-01-01"},
    ]
    validate_snapshot_coverage(manifests, start="2021-01-01", end="2025-12-31")


def test_validate_snapshot_coverage_fails_on_gap() -> None:
    manifests = [
        {"start": "2004-01-01", "end_exclusive": "2025-01-01"},
        {"start": "2025-02-01", "end_exclusive": "2026-01-01"},
    ]
    with pytest.raises(AssertionError, match="gap"):
        validate_snapshot_coverage(manifests, start="2021-01-01", end="2025-12-31")


def test_validate_snapshot_coverage_fails_when_requested_end_exceeds_extensions() -> None:
    manifests = [
        {"start": "2004-01-01", "end_exclusive": "2025-01-01"},
        {"start": "2025-01-01", "end_exclusive": "2026-01-01"},
    ]
    with pytest.raises(AssertionError, match="not fully covered"):
        validate_snapshot_coverage(manifests, start="2021-01-01", end="2026-08-21")


def test_select_prices_fails_closed_when_snapshot_lacks_open() -> None:
    frame = _prices().drop(columns="Open")
    with pytest.raises(AssertionError, match="Open"):
        select_prices(frame, tickers=["AAA"], start="2025-01-01", end="2026-01-01")


def test_select_prices_fails_closed_when_ticker_missing() -> None:
    with pytest.raises(AssertionError, match="CCC"):
        select_prices(_prices(), tickers=["AAA", "CCC"], start="2025-01-01", end="2026-01-01")


def test_build_baseline_emits_reproducible_spec_and_results() -> None:
    payload = build_baseline(
        _prices(),
        tickers=["AAA", "BBB"],
        start="2025-01-02",
        end="2025-12-31",
        half_life=126,
    )
    assert payload["schema_version"] == "investor2.session-state-baseline.v2"
    assert payload["specification"]["session_tilt_half_life"] == 126
    assert payload["specification"]["annualization_primary"] == "arithmetic mean daily component * 252"
    assert len(payload["results"]) == 2
    assert all(result["observations"] == 159 for result in payload["results"])
    assert all(result["latest_session_tilt"] is not None for result in payload["results"])
