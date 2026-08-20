#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SCHEMA_VERSION = "investor2.bls-nonfarm-business-labor-productivity-annual.v1"
SOURCE = "U.S. Bureau of Labor Statistics"
API_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
SERIES_IDS = {
    "percent_change": "PRS85006091",
    "index": "PRS85006093",
}
ANNUAL_PERIOD = "Q05"
FIRST_YEAR = 1948
MAX_YEARS_PER_REQUEST = 10
MAX_QUERIES_PER_DAY = 25
USER_AGENT = "KAFKA2306/investor2 (+https://github.com/KAFKA2306/investor2)"
OFFICIAL_URLS = {
    "api": API_URL,
    "api_docs": "https://www.bls.gov/developers/home.htm",
    "api_faq": "https://www.bls.gov/developers/api_faqs.htm",
    "series_metadata": "https://download.bls.gov/pub/time.series/pr/pr.series",
    "sector_metadata": "https://download.bls.gov/pub/time.series/pr/pr.sector",
    "measure_metadata": "https://download.bls.gov/pub/time.series/pr/pr.measure",
    "duration_metadata": "https://download.bls.gov/pub/time.series/pr/pr.duration",
    "period_metadata": "https://download.bls.gov/pub/time.series/pr/pr.period",
}


def request_windows(start_year: int, end_year: int) -> list[tuple[int, int]]:
    if start_year > end_year:
        raise ValueError("start_year must not exceed end_year")
    windows: list[tuple[int, int]] = []
    current = start_year
    while current <= end_year:
        window_end = min(current + MAX_YEARS_PER_REQUEST - 1, end_year)
        windows.append((current, window_end))
        current = window_end + 1
    return windows


def fetch_api_window(start_year: int, end_year: int, *, retries: int = 2) -> list[dict[str, Any]]:
    payload = json.dumps(
        {
            "seriesid": list(SERIES_IDS.values()),
            "startyear": str(start_year),
            "endyear": str(end_year),
        },
        separators=(",", ":"),
    ).encode("utf-8")
    request = Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        },
        method="POST",
    )

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with urlopen(request, timeout=45) as response:
                body = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt + 1 < retries:
                time.sleep(5)
                continue
            raise RuntimeError(f"BLS API request failed for {start_year}-{end_year}: {exc}") from exc

        if body.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(
                f"BLS API request did not succeed for {start_year}-{end_year}: "
                f"status={body.get('status')!r}, message={body.get('message')!r}"
            )
        series = body.get("Results", {}).get("series")
        if not isinstance(series, list):
            raise AssertionError(f"BLS API response missing Results.series for {start_year}-{end_year}")
        return series

    raise RuntimeError(f"BLS API request failed for {start_year}-{end_year}: {last_error}")


def fetch_api_history(start_year: int = FIRST_YEAR, end_year: int | None = None) -> list[dict[str, Any]]:
    resolved_end_year = end_year or datetime.now(UTC).year
    merged: dict[str, list[dict[str, Any]]] = {series_id: [] for series_id in SERIES_IDS.values()}
    windows = request_windows(start_year, resolved_end_year)
    if len(windows) > MAX_QUERIES_PER_DAY:
        raise AssertionError(f"BLS API request plan exceeds unregistered daily query limit: {len(windows)}")

    for start, end in windows:
        window_series = fetch_api_window(start, end)
        returned_ids = [entry.get("seriesID") for entry in window_series]
        expected_ids = list(SERIES_IDS.values())
        if sorted(returned_ids) != sorted(expected_ids):
            raise AssertionError(
                f"BLS API returned unexpected series IDs for {start}-{end}: "
                f"{returned_ids!r} != {expected_ids!r}"
            )
        for entry in window_series:
            data = entry.get("data")
            if not isinstance(data, list):
                raise AssertionError(f"BLS API series {entry.get('seriesID')} missing data list")
            merged[entry["seriesID"]].extend(data)

    return [{"seriesID": series_id, "data": data} for series_id, data in merged.items()]


def annual_values(series: list[dict[str, Any]], series_id: str) -> dict[int, float]:
    matches = [entry for entry in series if entry.get("seriesID") == series_id]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one BLS series {series_id}, found {len(matches)}")

    values: dict[int, float] = {}
    for observation in matches[0].get("data", []):
        if observation.get("period") != ANNUAL_PERIOD:
            continue
        year = int(observation["year"])
        if year in values:
            raise AssertionError(f"duplicate BLS annual observation: {series_id} {year}")
        values[year] = float(observation["value"])
    if not values:
        raise AssertionError(f"no annual observations found for BLS series {series_id}")
    return values


def build_payload(series: list[dict[str, Any]]) -> dict[str, Any]:
    percent_by_year = annual_values(series, SERIES_IDS["percent_change"])
    index_by_year = annual_values(series, SERIES_IDS["index"])

    percent_years = set(percent_by_year)
    index_years = set(index_by_year)
    missing_index = sorted(percent_years - index_years)
    if missing_index:
        raise AssertionError(f"BLS index missing annual years present in percent-change series: {missing_index}")

    years = sorted(percent_years)
    expected_years = list(range(years[0], years[-1] + 1))
    if years != expected_years:
        missing = sorted(set(expected_years) - percent_years)
        raise AssertionError(f"BLS annual percent-change history is not contiguous; missing years: {missing}")

    records = [
        {
            "year": year,
            "percent_change": percent_by_year[year],
            "index": index_by_year[year],
        }
        for year in years
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "source": SOURCE,
        "source_urls": OFFICIAL_URLS,
        "sector": "Nonfarm Business",
        "measure": "Labor productivity (output per hour)",
        "frequency": "annual",
        "annual_period": ANNUAL_PERIOD,
        "series_ids": SERIES_IDS,
        "first_year": years[0],
        "latest_year": years[-1],
        "records": records,
    }


def validate_historical_coverage(payload: dict[str, Any]) -> None:
    records = payload["records"]
    if payload["first_year"] != FIRST_YEAR:
        raise AssertionError(f"unexpected first annual percent-change year: {payload['first_year']} != {FIRST_YEAR}")

    stale_before = max(2025, datetime.now(UTC).year - 2)
    if payload["latest_year"] < stale_before:
        raise AssertionError(
            f"BLS annual history is stale: latest year {payload['latest_year']} < required {stale_before}"
        )

    expected_count = payload["latest_year"] - payload["first_year"] + 1
    if len(records) != expected_count:
        raise AssertionError(f"non-contiguous annual record count: {len(records)} != {expected_count}")


def materialize_snapshot(payload: dict[str, Any], output_dir: Path, latest_path: Path | None) -> Path:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / (
        f"bls_nonfarm_business_labor_productivity_annual_{payload['latest_year']}_{digest[:12]}.json"
    )
    artifact.write_text(serialized, encoding="utf-8")
    if latest_path is not None:
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(serialized, encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize BLS Nonfarm Business annual labor productivity from the official Public Data API."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--latest-path", type=Path)
    parser.add_argument("--end-year", type=int)
    args = parser.parse_args()

    payload = build_payload(fetch_api_history(end_year=args.end_year))
    validate_historical_coverage(payload)
    artifact = materialize_snapshot(payload, args.output_dir, args.latest_path)
    resolved_artifact = artifact.resolve()
    root = Path.cwd().resolve()
    if resolved_artifact.is_relative_to(root):
        print(resolved_artifact.relative_to(root).as_posix())
    else:
        print(artifact.as_posix())


if __name__ == "__main__":
    main()
