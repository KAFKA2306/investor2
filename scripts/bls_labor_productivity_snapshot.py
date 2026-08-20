#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = "investor2.bls-nonfarm-business-labor-productivity-annual.v1"
SOURCE = "U.S. Bureau of Labor Statistics"
SECTOR_NAME = "Nonfarm Business"
MEASURE_NAME = "Labor productivity (output per hour)"
PERCENT_CHANGE_DURATION = "% Change same quarter 1 year ago"
INDEX_DURATION_PREFIX = "Index ("
ANNUAL_PERIOD_NAME = "Annual Average"
OFFICIAL_URLS = {
    "series": "https://download.bls.gov/pub/time.series/pr/pr.series",
    "sector": "https://download.bls.gov/pub/time.series/pr/pr.sector",
    "measure": "https://download.bls.gov/pub/time.series/pr/pr.measure",
    "duration": "https://download.bls.gov/pub/time.series/pr/pr.duration",
    "period": "https://download.bls.gov/pub/time.series/pr/pr.period",
    "data": "https://download.bls.gov/pub/time.series/pr/pr.data.1.AllData",
}


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = [cell.strip() for cell in next(reader)]
        except StopIteration as exc:
            raise AssertionError(f"empty BLS file: {path}") from exc
        if not header or any(not name for name in header):
            raise AssertionError(f"invalid BLS header: {path}")
        rows: list[dict[str, str]] = []
        for raw in reader:
            if not raw or not any(cell.strip() for cell in raw):
                continue
            padded = list(raw) + [""] * max(0, len(header) - len(raw))
            rows.append({name: padded[index].strip() for index, name in enumerate(header)})
    if not rows:
        raise AssertionError(f"BLS file has no data rows: {path}")
    return rows


def lookup_code(rows: Iterable[dict[str, str]], code_field: str, name_field: str, expected_name: str) -> str:
    matches = [row[code_field] for row in rows if row.get(name_field) == expected_name]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one {name_field}={expected_name!r}, found {len(matches)}")
    return matches[0]


def lookup_index_duration(rows: Iterable[dict[str, str]]) -> tuple[str, str]:
    matches = [
        (row["duration_code"], row["duration_text"])
        for row in rows
        if row.get("duration_text", "").startswith(INDEX_DURATION_PREFIX)
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one BLS index duration, found {len(matches)}")
    return matches[0]


def select_series(
    rows: Iterable[dict[str, str]], *, sector_code: str, measure_code: str, duration_code: str
) -> dict[str, str]:
    matches = [
        row
        for row in rows
        if row.get("sector_code") == sector_code
        and row.get("measure_code") == measure_code
        and row.get("duration_code") == duration_code
    ]
    if len(matches) != 1:
        raise AssertionError(
            "expected exactly one BLS series for "
            f"sector={sector_code}, measure={measure_code}, duration={duration_code}; found {len(matches)}"
        )
    return matches[0]


def annual_values(
    rows: Iterable[dict[str, str]], *, series_id: str, annual_period: str
) -> dict[int, float]:
    values: dict[int, float] = {}
    for row in rows:
        if row.get("series_id") != series_id or row.get("period") != annual_period:
            continue
        year = int(row["year"])
        if year in values:
            raise AssertionError(f"duplicate BLS annual observation: {series_id} {year}")
        values[year] = float(row["value"])
    if not values:
        raise AssertionError(f"no annual observations found for BLS series {series_id}")
    return values


def build_payload(
    *,
    series_path: Path,
    sector_path: Path,
    measure_path: Path,
    duration_path: Path,
    period_path: Path,
    data_path: Path,
) -> dict[str, Any]:
    series_rows = read_tsv(series_path)
    sector_rows = read_tsv(sector_path)
    measure_rows = read_tsv(measure_path)
    duration_rows = read_tsv(duration_path)
    period_rows = read_tsv(period_path)
    data_rows = read_tsv(data_path)

    sector_code = lookup_code(sector_rows, "sector_code", "sector_name", SECTOR_NAME)
    measure_code = lookup_code(measure_rows, "measure_code", "measure_text", MEASURE_NAME)
    percent_duration_code = lookup_code(
        duration_rows, "duration_code", "duration_text", PERCENT_CHANGE_DURATION
    )
    index_duration_code, index_duration_text = lookup_index_duration(duration_rows)
    annual_period = lookup_code(period_rows, "period", "period_name", ANNUAL_PERIOD_NAME)

    percent_series = select_series(
        series_rows,
        sector_code=sector_code,
        measure_code=measure_code,
        duration_code=percent_duration_code,
    )
    index_series = select_series(
        series_rows,
        sector_code=sector_code,
        measure_code=measure_code,
        duration_code=index_duration_code,
    )

    percent_by_year = annual_values(
        data_rows, series_id=percent_series["series_id"], annual_period=annual_period
    )
    index_by_year = annual_values(data_rows, series_id=index_series["series_id"], annual_period=annual_period)

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
        "sector": SECTOR_NAME,
        "measure": MEASURE_NAME,
        "frequency": "annual",
        "annual_period": {"code": annual_period, "name": ANNUAL_PERIOD_NAME},
        "percent_change_definition": PERCENT_CHANGE_DURATION,
        "index_definition": index_duration_text,
        "series_ids": {
            "percent_change": percent_series["series_id"],
            "index": index_series["series_id"],
        },
        "first_year": years[0],
        "latest_year": years[-1],
        "records": records,
    }


def validate_historical_coverage(payload: dict[str, Any]) -> None:
    records = payload["records"]
    if payload["first_year"] != 1948:
        raise AssertionError(f"unexpected first annual percent-change year: {payload['first_year']} != 1948")
    if payload["latest_year"] < 2025:
        raise AssertionError(f"BLS annual history is stale: latest year {payload['latest_year']} < 2025")
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
        description="Materialize BLS Nonfarm Business annual labor productivity from official flat files."
    )
    parser.add_argument("--series", type=Path, required=True)
    parser.add_argument("--sector", type=Path, required=True)
    parser.add_argument("--measure", type=Path, required=True)
    parser.add_argument("--duration", type=Path, required=True)
    parser.add_argument("--period", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--latest-path", type=Path)
    args = parser.parse_args()

    payload = build_payload(
        series_path=args.series,
        sector_path=args.sector,
        measure_path=args.measure,
        duration_path=args.duration,
        period_path=args.period,
        data_path=args.data,
    )
    validate_historical_coverage(payload)
    artifact = materialize_snapshot(payload, args.output_dir, args.latest_path)
    resolved_artifact = artifact.resolve()
    root = Path.cwd().resolve()
    print(resolved_artifact.relative_to(root).as_posix() if resolved_artifact.is_relative_to(root) else artifact.as_posix())


if __name__ == "__main__":
    main()
