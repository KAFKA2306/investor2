from __future__ import annotations

import pandas as pd

from scripts.alphazerobeta_build_market_snapshot import normalize_download
from scripts.alphazerobeta_prepare import normalize_benchmark_frame, normalize_price_frame


def test_normalize_download_converts_yfinance_multiindex_to_long_rows() -> None:
    index = pd.DatetimeIndex(["2024-01-02", "2024-01-03"], name="Date")
    columns = pd.MultiIndex.from_product([["AAA", "BBB"], ["Close", "Adj Close", "Volume"]])
    raw = pd.DataFrame(
        [
            [10.0, 9.5, 100.0, 20.0, 19.0, 200.0],
            [11.0, 10.5, 110.0, 21.0, 20.0, 210.0],
        ],
        index=index,
        columns=columns,
    )

    result = normalize_download(raw, ["AAA", "BBB"])

    assert result["Ticker"].tolist() == ["AAA", "AAA", "BBB", "BBB"]
    assert "AdjClose" in result.columns
    assert result["Date"].dt.tz is None


def test_cached_price_normalization_prefers_adjusted_close() -> None:
    cached = pd.DataFrame(
        {
            "Ticker": ["AAA", "AAA"],
            "Date": ["2024-01-02", "2024-01-03"],
            "Close": [10.0, 11.0],
            "AdjClose": [9.0, 10.0],
            "Volume": [100.0, 110.0],
        }
    )

    result = normalize_price_frame(cached)

    assert result["Code"].tolist() == ["AAA", "AAA"]
    assert result["Close"].tolist() == [9.0, 10.0]


def test_cached_benchmark_normalization_prefers_adjusted_close() -> None:
    cached = pd.DataFrame(
        {
            "Ticker": ["SPY", "SPY"],
            "Date": ["2024-01-02", "2024-01-03"],
            "Close": [100.0, 110.0],
            "AdjClose": [90.0, 99.0],
            "Volume": [1000.0, 1100.0],
        }
    )

    result = normalize_benchmark_frame(cached)

    assert result["Close"].tolist() == [90.0, 99.0]
    assert result["BenchmarkReturn"].iloc[1] > 0
