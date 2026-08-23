from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from yfinance import EquityQuery
from yfinance.exceptions import YFRateLimitError

import scripts.alphazerobeta_build_market_snapshot as market_snapshot_builder
from scripts.alphazerobeta_build_market_snapshot import (
    DEFAULT_MAX_REQUEST_ATTEMPTS,
    DEFAULT_RETRY_BASE_SECONDS,
    DEFAULT_STORAGE_PREFIX,
    normalize_download,
    parse_args,
    screen_with_retry,
)
from scripts.alphazerobeta_prepare import normalize_benchmark_frame, normalize_price_frame
from src.research.market_snapshot import (
    MarketSnapshot,
    load_benchmark,
    load_manifest,
    load_prices,
    load_prices_from_snapshots,
    load_universe,
)


def test_market_snapshot_defaults_to_japan_all_equities(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["alphazerobeta_build_market_snapshot.py"])

    args = parse_args()

    assert args.regions == "jp"
    assert args.benchmark == "1306.T"
    assert args.start == "2004-01-01"
    assert args.end == "2025-01-01"
    assert args.storage_prefix == DEFAULT_STORAGE_PREFIX
    assert args.storage_prefix.endswith("/yahoo-market-cache/jp-v1")
    assert args.max_request_attempts == DEFAULT_MAX_REQUEST_ATTEMPTS
    assert args.retry_base_seconds == DEFAULT_RETRY_BASE_SECONDS


def test_screen_with_retry_recovers_after_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    sleeps: list[float] = []

    def fake_screen(*args: object, **kwargs: object) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls < 3:
            raise YFRateLimitError()
        return {"quotes": [{"symbol": "7203.T"}], "total": 1}

    monkeypatch.setattr(market_snapshot_builder.yf, "screen", fake_screen)
    monkeypatch.setattr(market_snapshot_builder.time, "sleep", sleeps.append)

    result = screen_with_retry(
        EquityQuery("eq", ["region", "jp"]),
        region="jp",
        offset=0,
        page_size=250,
        max_attempts=4,
        retry_base_seconds=2.0,
    )

    assert result["quotes"][0]["symbol"] == "7203.T"
    assert calls == 3
    assert sleeps == [2.0, 4.0]


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


def _write_snapshot(root: Path, *, date: str, close: float) -> MarketSnapshot:
    price_root = root / "prices" / "us"
    price_root.mkdir(parents=True)
    universe = pd.DataFrame({"Ticker": ["AAA"], "Region": ["us"]})
    prices = pd.DataFrame(
        {
            "Ticker": ["AAA"],
            "Date": [date],
            "Open": [close],
            "AdjClose": [close],
            "Close": [close],
            "Volume": [100.0],
        }
    )
    benchmark = pd.DataFrame(
        {"Ticker": ["SPY"], "Date": [date], "AdjClose": [100.0], "Close": [100.0], "Volume": [1000.0]}
    )
    universe.to_parquet(root / "universe.parquet", index=False)
    prices.to_parquet(price_root / "part-00000.parquet", index=False)
    benchmark.to_parquet(root / "benchmark.parquet", index=False)
    (root / "manifest.json").write_text(
        json.dumps({"schema_version": "investor2.market-snapshot.v2", "ticker_count": 1}), encoding="utf-8"
    )
    return MarketSnapshot(root)


def test_materialized_snapshot_reads_without_hugging_face_credentials(tmp_path: Path) -> None:
    snapshot = _write_snapshot(tmp_path / "snapshot", date="2024-01-02", close=10.0)

    assert load_manifest(snapshot)["ticker_count"] == 1
    assert load_universe(snapshot)["Ticker"].tolist() == ["AAA"]
    assert load_prices(snapshot, regions=["us"])["Ticker"].tolist() == ["AAA"]
    assert load_benchmark(snapshot)["Ticker"].tolist() == ["SPY"]


def test_composed_snapshots_append_non_overlapping_years(tmp_path: Path) -> None:
    base = _write_snapshot(tmp_path / "base", date="2024-12-31", close=10.0)
    extension = _write_snapshot(tmp_path / "extension", date="2025-01-02", close=11.0)

    result = load_prices_from_snapshots([base, extension], regions=["us"])

    assert result["Date"].dt.strftime("%Y-%m-%d").tolist() == ["2024-12-31", "2025-01-02"]
    assert result["Close"].tolist() == [10.0, 11.0]


def test_composed_snapshots_reject_overlap(tmp_path: Path) -> None:
    left = _write_snapshot(tmp_path / "left", date="2025-01-02", close=10.0)
    right = _write_snapshot(tmp_path / "right", date="2025-01-02", close=11.0)

    with pytest.raises(AssertionError, match="duplicate Ticker/Date"):
        load_prices_from_snapshots([left, right], regions=["us"])
