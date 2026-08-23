from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from scripts.alphazerobeta_build_market_snapshot import normalize_download
from scripts.alphazerobeta_prepare import normalize_benchmark_frame, normalize_price_frame
from src.research.market_snapshot import MarketSnapshot, load_benchmark, load_manifest, load_prices, load_universe


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


def test_materialized_snapshot_reads_without_hugging_face_credentials(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "snapshot"
    price_root = snapshot_root / "prices" / "us"
    price_root.mkdir(parents=True)
    universe = pd.DataFrame({"Ticker": ["AAA"], "Region": ["us"]})
    prices = pd.DataFrame(
        {"Ticker": ["AAA"], "Date": ["2024-01-02"], "AdjClose": [10.0], "Close": [10.0], "Volume": [100.0]}
    )
    benchmark = pd.DataFrame(
        {"Ticker": ["SPY"], "Date": ["2024-01-02"], "AdjClose": [100.0], "Close": [100.0], "Volume": [1000.0]}
    )
    universe.to_parquet(snapshot_root / "universe.parquet", index=False)
    prices.to_parquet(price_root / "part-00000.parquet", index=False)
    benchmark.to_parquet(snapshot_root / "benchmark.parquet", index=False)
    (snapshot_root / "manifest.json").write_text(
        json.dumps({"schema_version": "investor2.market-snapshot.v2", "ticker_count": 1}), encoding="utf-8"
    )

    snapshot = MarketSnapshot(snapshot_root)

    assert load_manifest(snapshot)["ticker_count"] == 1
    assert load_universe(snapshot)["Ticker"].tolist() == ["AAA"]
    assert load_prices(snapshot, regions=["us"])["Ticker"].tolist() == ["AAA"]
    assert load_benchmark(snapshot)["Ticker"].tolist() == ["SPY"]
