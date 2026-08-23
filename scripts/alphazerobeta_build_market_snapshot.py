#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import shutil
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf
from yfinance import EquityQuery
from yfinance.exceptions import YFRateLimitError

DEFAULT_STORAGE_PREFIX = "central/investor2/private/yahoo-market-cache/jp-v1"
DEFAULT_MAX_REQUEST_ATTEMPTS = 6
DEFAULT_RETRY_BASE_SECONDS = 5.0
ALL_REGIONS = (
    "ae",
    "ar",
    "at",
    "au",
    "be",
    "br",
    "ca",
    "ch",
    "cl",
    "cn",
    "co",
    "cz",
    "de",
    "dk",
    "ee",
    "eg",
    "es",
    "fi",
    "fr",
    "gb",
    "gr",
    "hk",
    "hu",
    "id",
    "ie",
    "il",
    "in",
    "is",
    "it",
    "jp",
    "kr",
    "kw",
    "lk",
    "lt",
    "lv",
    "mx",
    "my",
    "nl",
    "no",
    "nz",
    "pe",
    "ph",
    "pk",
    "pl",
    "pt",
    "qa",
    "ro",
    "ru",
    "sa",
    "se",
    "sg",
    "sr",
    "th",
    "tr",
    "tw",
    "us",
    "ve",
    "vn",
    "za",
)


def log_event(event: str, **fields: object) -> None:
    payload: dict[str, object] = {
        "ts_utc": datetime.now(UTC).isoformat(),
        "component": "alphazerobeta_yahoo_market_snapshot",
        "event": event,
        **fields,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str), flush=True)


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def require_repair_runtime() -> None:
    scipy_available = importlib.util.find_spec("scipy") is not None
    log_event(
        "dependency_preflight",
        python=sys.version.split()[0],
        pandas=package_version("pandas"),
        pyarrow=package_version("pyarrow"),
        yfinance=package_version("yfinance"),
        scipy=package_version("scipy"),
        scipy_available=scipy_available,
        yfinance_repair=True,
    )
    if not scipy_available:
        log_event(
            "dependency_preflight_failed",
            missing_dependency="scipy",
            reason="yfinance repair=True requires SciPy at runtime",
        )
        raise RuntimeError("missing runtime dependency: scipy is required by yfinance download(repair=True)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build one immutable Yahoo/yfinance equity snapshot locally.")
    parser.add_argument("--start", default="2004-01-01")
    parser.add_argument("--end", default="2025-01-01", help="Exclusive end date")
    parser.add_argument("--regions", default="jp", help="Comma-separated Yahoo regions or 'all'")
    parser.add_argument("--benchmark", default="1306.T", help="Broad Japan benchmark proxy; default is TOPIX ETF")
    parser.add_argument("--storage-prefix", default=DEFAULT_STORAGE_PREFIX)
    parser.add_argument("--page-size", type=int, default=250)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--request-pause", type=float, default=0.25)
    parser.add_argument("--max-request-attempts", type=int, default=DEFAULT_MAX_REQUEST_ATTEMPTS)
    parser.add_argument("--retry-base-seconds", type=float, default=DEFAULT_RETRY_BASE_SECONDS)
    parser.add_argument("--output-dir", type=Path, default=Path("cache/alphazerobeta-market-snapshot"))
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_output(root: Path, *, overwrite: bool) -> None:
    if (root / "manifest.json").exists() and not overwrite:
        raise RuntimeError(f"{root}/manifest.json already exists; refusing to overwrite immutable snapshot")
    if root.exists() and overwrite:
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)


def _quotes(response: dict[str, Any]) -> list[dict[str, Any]]:
    raw = response.get("quotes", [])
    if not isinstance(raw, list):
        raise AssertionError("yfinance screener response quotes must be a list")
    return [row for row in raw if isinstance(row, dict)]


def screen_with_retry(
    query: EquityQuery,
    *,
    region: str,
    offset: int,
    page_size: int,
    max_attempts: int,
    retry_base_seconds: float,
) -> dict[str, Any]:
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")
    for attempt in range(1, max_attempts + 1):
        started = time.monotonic()
        try:
            response = yf.screen(query, offset=offset, size=page_size, sortField="ticker", sortAsc=True)
            if not isinstance(response, dict):
                raise AssertionError(f"unexpected yfinance screen response for region={region}")
            log_event(
                "universe_page_success",
                region=region,
                offset=offset,
                page_size=page_size,
                attempt=attempt,
                quote_count=len(_quotes(response)),
                elapsed_seconds=round(time.monotonic() - started, 3),
            )
            return response
        except YFRateLimitError as exc:
            if attempt == max_attempts:
                log_event(
                    "universe_page_failed",
                    region=region,
                    offset=offset,
                    attempt=attempt,
                    exception_type=type(exc).__name__,
                    exception=str(exc),
                )
                raise
            delay = retry_base_seconds * (2 ** (attempt - 1))
            log_event(
                "yahoo_rate_limit_retry",
                region=region,
                offset=offset,
                attempt=attempt,
                max_attempts=max_attempts,
                sleep_seconds=delay,
            )
            time.sleep(delay)
        except Exception as exc:
            log_event(
                "universe_page_failed",
                region=region,
                offset=offset,
                attempt=attempt,
                exception_type=type(exc).__name__,
                exception=str(exc),
            )
            raise
    raise AssertionError("unreachable")


def discover_region(
    region: str,
    *,
    page_size: int,
    pause: float,
    max_attempts: int = DEFAULT_MAX_REQUEST_ATTEMPTS,
    retry_base_seconds: float = DEFAULT_RETRY_BASE_SECONDS,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    offset = 0
    query = EquityQuery("eq", ["region", region])
    log_event("universe_region_start", region=region, page_size=page_size)
    while True:
        response = screen_with_retry(
            query,
            region=region,
            offset=offset,
            page_size=page_size,
            max_attempts=max_attempts,
            retry_base_seconds=retry_base_seconds,
        )
        page = _quotes(response)
        new_count = 0
        for quote in page:
            symbol = str(quote.get("symbol", "")).strip()
            if not symbol or symbol in seen:
                continue
            seen.add(symbol)
            new_count += 1
            rows.append(
                {
                    "Ticker": symbol,
                    "Region": region,
                    "Exchange": str(quote.get("exchange", "")),
                    "QuoteType": str(quote.get("quoteType", "EQUITY")),
                    "ShortName": str(quote.get("shortName", "")),
                    "LongName": str(quote.get("longName", "")),
                    "Currency": str(quote.get("currency", "")),
                }
            )
        total = response.get("total")
        offset += len(page)
        if not page or new_count == 0 or len(page) < page_size or (isinstance(total, int) and offset >= total):
            break
        time.sleep(pause)
    log_event("universe_region_complete", region=region, ticker_count=len(rows))
    return pd.DataFrame(rows)


def discover_universe(
    regions: list[str],
    *,
    page_size: int,
    pause: float,
    max_attempts: int = DEFAULT_MAX_REQUEST_ATTEMPTS,
    retry_base_seconds: float = DEFAULT_RETRY_BASE_SECONDS,
) -> pd.DataFrame:
    frames = []
    for region in regions:
        frame = discover_region(
            region,
            page_size=page_size,
            pause=pause,
            max_attempts=max_attempts,
            retry_base_seconds=retry_base_seconds,
        )
        log_event("universe_region_result", region=region, tickers=len(frame))
        if not frame.empty:
            frames.append(frame)
    if not frames:
        raise AssertionError("yfinance discovery returned no equities")
    universe = pd.concat(frames, ignore_index=True)
    result = (
        universe.drop_duplicates(["Region", "Ticker"], keep="first")
        .sort_values(["Region", "Ticker"])
        .reset_index(drop=True)
    )
    log_event("universe_complete", regions=regions, ticker_count=len(result))
    return result


def normalize_download(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame()
    if not isinstance(raw.columns, pd.MultiIndex):
        if len(tickers) != 1:
            raise AssertionError("expected MultiIndex columns for multi-ticker download")
        raw = raw.copy()
        raw.columns = pd.MultiIndex.from_product([tickers, raw.columns])
    available = set(map(str, raw.columns.get_level_values(0)))
    parts = []
    for ticker in tickers:
        if ticker not in available:
            continue
        frame = raw[ticker].reset_index()
        frame = frame.rename(
            columns={"Adj Close": "AdjClose", "Stock Splits": "StockSplits", "Capital Gains": "CapitalGains"}
        )
        frame.insert(0, "Ticker", ticker)
        parts.append(frame)
    if not parts:
        return pd.DataFrame()
    result = pd.concat(parts, ignore_index=True)
    date_column = "Date" if "Date" in result.columns else "Datetime"
    if date_column not in result.columns:
        raise AssertionError("downloaded price frame has no Date/Datetime column")
    result = result.rename(columns={date_column: "Date"})
    result["Date"] = pd.to_datetime(result["Date"], utc=True).dt.tz_convert(None)
    return result.sort_values(["Ticker", "Date"]).reset_index(drop=True)


def download_prices(tickers: list[str], *, start: str, end: str, context: str) -> pd.DataFrame:
    started = time.monotonic()
    log_event(
        "price_download_start",
        context=context,
        ticker_count=len(tickers),
        ticker_sample=tickers[:5],
        start=start,
        end=end,
        repair=True,
    )
    try:
        raw = yf.download(
            tickers,
            start=start,
            end=end,
            interval="1d",
            auto_adjust=False,
            actions=True,
            repair=True,
            keepna=False,
            group_by="ticker",
            threads=True,
            progress=False,
            timeout=30,
        )
        frame = pd.DataFrame() if raw is None else normalize_download(raw, tickers)
    except Exception as exc:
        log_event(
            "price_download_exception",
            context=context,
            ticker_count=len(tickers),
            exception_type=type(exc).__name__,
            exception=str(exc),
            elapsed_seconds=round(time.monotonic() - started, 3),
        )
        raise
    returned_tickers = int(frame["Ticker"].nunique()) if not frame.empty and "Ticker" in frame.columns else 0
    log_event(
        "price_download_complete" if not frame.empty else "price_download_empty",
        context=context,
        requested_tickers=len(tickers),
        returned_tickers=returned_tickers,
        rows=len(frame),
        elapsed_seconds=round(time.monotonic() - started, 3),
    )
    return frame


def write_region_prices(
    universe: pd.DataFrame,
    root: Path,
    *,
    start: str,
    end: str,
    batch_size: int,
    pause: float,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for region, group in universe.groupby("Region", observed=True):
        tickers = group["Ticker"].astype(str).tolist()
        region_dir = root / "prices" / str(region)
        region_dir.mkdir(parents=True, exist_ok=True)
        rows = 0
        nonempty_batches = 0
        log_event("price_region_start", region=str(region), ticker_count=len(tickers), batch_size=batch_size)
        for index in range(0, len(tickers), batch_size):
            batch_number = index // batch_size
            batch = tickers[index : index + batch_size]
            frame = download_prices(batch, start=start, end=end, context=f"region={region},batch={batch_number}")
            if not frame.empty:
                frame.to_parquet(region_dir / f"part-{batch_number:05d}.parquet", index=False, compression="zstd")
                rows += len(frame)
                nonempty_batches += 1
            log_event(
                "price_batch_result",
                region=str(region),
                batch=batch_number,
                requested_tickers=len(batch),
                returned_tickers=int(frame["Ticker"].nunique()) if not frame.empty else 0,
                rows=len(frame),
                cumulative_rows=rows,
            )
            time.sleep(pause)
        counts[str(region)] = rows
        log_event(
            "price_region_complete",
            region=str(region),
            ticker_count=len(tickers),
            rows=rows,
            nonempty_batches=nonempty_batches,
        )
    return counts


def file_manifest(root: Path) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return entries


def main() -> None:
    args = parse_args()
    regions = (
        list(ALL_REGIONS)
        if args.regions.lower() == "all"
        else [value.strip().lower() for value in args.regions.split(",") if value.strip()]
    )
    unknown = sorted(set(regions) - set(ALL_REGIONS))
    if unknown:
        raise ValueError(f"unsupported Yahoo regions: {unknown}")
    root = args.output_dir
    log_event(
        "snapshot_start",
        regions=regions,
        start=args.start,
        end=args.end,
        benchmark=args.benchmark,
        batch_size=args.batch_size,
        output_dir=str(root),
        storage_prefix=args.storage_prefix,
    )
    require_repair_runtime()
    prepare_output(root, overwrite=args.overwrite)

    universe = discover_universe(
        regions,
        page_size=args.page_size,
        pause=args.request_pause,
        max_attempts=args.max_request_attempts,
        retry_base_seconds=args.retry_base_seconds,
    )
    universe.to_parquet(root / "universe.parquet", index=False, compression="zstd")
    row_counts = write_region_prices(
        universe,
        root,
        start=args.start,
        end=args.end,
        batch_size=args.batch_size,
        pause=args.request_pause,
    )
    log_event("benchmark_download_start", benchmark=args.benchmark)
    benchmark = download_prices([args.benchmark], start=args.start, end=args.end, context="benchmark")
    if benchmark.empty:
        log_event("benchmark_download_failed", benchmark=args.benchmark, reason="empty_frame")
        raise AssertionError(f"benchmark download failed: {args.benchmark}")
    benchmark.to_parquet(root / "benchmark.parquet", index=False, compression="zstd")
    files = file_manifest(root)

    manifest: dict[str, object] = {
        "schema_version": "investor2.market-snapshot.v2",
        "source": "Yahoo Finance via yfinance",
        "fetched_at_utc": datetime.now(UTC).isoformat(),
        "start": args.start,
        "end_exclusive": args.end,
        "regions": regions,
        "ticker_count": int(len(universe)),
        "ticker_count_by_region": {
            str(key): int(value) for key, value in universe.groupby("Region", observed=True)["Ticker"].nunique().items()
        },
        "price_rows_by_region": row_counts,
        "benchmark": args.benchmark,
        "immutable": True,
        "files": files,
        "storage_contract": {
            "writer_repository": "KAFKA2306/semiconductor-earnings-model",
            "bucket": "k4fka/kafka-data-lake",
            "prefix": args.storage_prefix,
            "consumer_repository_authentication": False,
        },
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    log_event(
        "snapshot_complete",
        output_dir=str(root),
        ticker_count=manifest["ticker_count"],
        price_rows_by_region=row_counts,
        files=len(files),
    )


if __name__ == "__main__":
    main()
