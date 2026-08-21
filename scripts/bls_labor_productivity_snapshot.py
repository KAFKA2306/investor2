#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, override

SCHEMA_VERSION = "investor2.bls-nonfarm-business-labor-productivity-annual.v1"
SOURCE = "U.S. Bureau of Labor Statistics"
SERIES_REPORT_URL = "https://data.bls.gov/series-report"
SERIES_OUTPUT_URL = "https://data.bls.gov/pdq/SurveyOutputServlet"
SERIES_URLS = {
    "percent_change": "https://data.bls.gov/timeseries/PRS85006091",
    "index": "https://data.bls.gov/timeseries/PRS85006093",
}
OFFICIAL_URLS = {
    "series_report": SERIES_REPORT_URL,
    "series_output": SERIES_OUTPUT_URL,
    "percent_change_series": SERIES_URLS["percent_change"],
    "index_series": SERIES_URLS["index"],
    "tables": "https://www.bls.gov/productivity/tables/home.htm",
    "latest_release": "https://www.bls.gov/news.release/prod2.htm",
}
SERIES_IDS = {
    "percent_change": "PRS85006091",
    "index": "PRS85006093",
}
EXPECTED_SECTOR = "Nonfarm Business"
EXPECTED_MEASURE = "Labor productivity (output per hour)"
EXPECTED_PERCENT_DURATION = "% Change same quarter 1 year ago"
EXPECTED_DATA_HEADER = ["Year", "Qtr1", "Qtr2", "Qtr3", "Qtr4", "Annual"]
FIRST_YEAR = 1948
NUMBER_RE = re.compile(r"^[+-]?\d+(?:\.\d+)?$")
FOOTNOTE_RE = re.compile(r"^[A-Z]+\s*:\s*\S.*$")


class SeriesReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.catalog: dict[str, str] = {}
        self.data_rows: list[list[str]] = []
        self._table: str | None = None
        self._row: list[str] | None = None
        self._cell_tag: str | None = None
        self._cell_parts: list[str] = []

    @staticmethod
    def _attrs(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
        return {key: value or "" for key, value in attrs}

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = self._attrs(attrs)
        if tag == "table":
            table_id = attributes.get("id", "")
            classes = set(attributes.get("class", "").split())
            if table_id.startswith("catalog") or "catalog" in classes:
                self._table = "catalog"
            elif table_id.startswith("table") and "regular-data" in classes:
                self._table = "data"
            else:
                self._table = None
        elif tag == "tr" and self._table in {"catalog", "data"}:
            self._row = []
        elif tag in {"th", "td"} and self._row is not None:
            self._cell_tag = tag
            self._cell_parts = []

    @override
    def handle_data(self, data: str) -> None:
        if self._cell_tag is not None:
            self._cell_parts.append(data)

    @override
    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._cell_tag == tag and self._row is not None:
            text = " ".join("".join(self._cell_parts).split())
            self._row.append(text)
            self._cell_tag = None
            self._cell_parts = []
        elif tag == "tr" and self._row is not None:
            if self._table == "catalog" and len(self._row) >= 2:
                self.catalog[self._row[0].rstrip(":")] = self._row[1]
            elif self._table == "data" and self._row:
                self.data_rows.append(self._row)
            self._row = None
        elif tag == "table":
            self._table = None


def parse_series_report(path: Path, *, expected_series_id: str) -> tuple[dict[str, str], dict[int, float]]:
    parser = SeriesReportParser()
    parser.feed(path.read_text(encoding="utf-8", errors="strict"))
    parser.close()

    if parser.catalog.get("Series Id") != expected_series_id:
        raise AssertionError(f"unexpected BLS series id: {parser.catalog.get('Series Id')!r} != {expected_series_id!r}")
    if parser.catalog.get("Sector") != EXPECTED_SECTOR:
        raise AssertionError(f"unexpected BLS sector: {parser.catalog.get('Sector')!r}")
    if parser.catalog.get("Measure") != EXPECTED_MEASURE:
        raise AssertionError(f"unexpected BLS measure: {parser.catalog.get('Measure')!r}")

    if not parser.data_rows or parser.data_rows[0] != EXPECTED_DATA_HEADER:
        actual = parser.data_rows[0] if parser.data_rows else None
        raise AssertionError(f"unexpected BLS Series Report table header: {actual!r}")

    annual_values: dict[int, float] = {}
    for row in parser.data_rows[1:]:
        if len(row) == 1 and FOOTNOTE_RE.fullmatch(row[0]):
            continue
        if len(row) != len(EXPECTED_DATA_HEADER):
            raise AssertionError(f"unexpected BLS Series Report row width: {row!r}")
        if not row[0].isdigit():
            raise AssertionError(f"unexpected BLS Series Report year: {row[0]!r}")
        year = int(row[0])
        annual = row[-1]
        if not NUMBER_RE.fullmatch(annual):
            # The current incomplete calendar year can have no annual value yet.
            continue
        if year in annual_values:
            raise AssertionError(f"duplicate BLS annual observation: {expected_series_id} {year}")
        annual_values[year] = float(annual)

    if not annual_values:
        raise AssertionError(f"BLS Series Report contains no annual values for {expected_series_id}")
    return parser.catalog, annual_values


def build_payload(percent_path: Path, index_path: Path) -> dict[str, Any]:
    percent_catalog, percent_by_year = parse_series_report(
        percent_path, expected_series_id=SERIES_IDS["percent_change"]
    )
    index_catalog, index_by_year = parse_series_report(index_path, expected_series_id=SERIES_IDS["index"])

    if percent_catalog.get("Duration") != EXPECTED_PERCENT_DURATION:
        raise AssertionError(f"unexpected BLS percent-change duration: {percent_catalog.get('Duration')!r}")

    percent_years = set(percent_by_year)
    index_years = set(index_by_year)
    if percent_years != index_years:
        missing_index = sorted(percent_years - index_years)
        extra_index = sorted(index_years - percent_years)
        raise AssertionError(
            f"BLS annual series year mismatch; missing index years={missing_index}, extra index years={extra_index}"
        )

    years = sorted(percent_years)
    expected_years = list(range(years[0], years[-1] + 1))
    if years != expected_years:
        missing = sorted(set(expected_years) - percent_years)
        raise AssertionError(f"BLS annual history is not contiguous; missing years: {missing}")

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
        "sector": EXPECTED_SECTOR,
        "measure": EXPECTED_MEASURE,
        "frequency": "annual",
        "annual_value_source": "BLS Series Report annual average column",
        "series_ids": SERIES_IDS,
        "series_catalog": {
            "percent_change": percent_catalog,
            "index": index_catalog,
        },
        "first_year": years[0],
        "latest_year": years[-1],
        "records": records,
    }


def validate_historical_coverage(payload: dict[str, Any]) -> None:
    first_year = payload.get("first_year")
    latest_year = payload.get("latest_year")
    records = payload.get("records")
    if first_year != FIRST_YEAR:
        raise AssertionError(f"unexpected first annual year: {first_year!r} != {FIRST_YEAR}")
    if not isinstance(latest_year, int):
        raise AssertionError(f"invalid latest year: {latest_year!r}")
    if not isinstance(records, list):
        raise AssertionError("BLS payload records must be a list")

    stale_before = max(2025, datetime.now(UTC).year - 2)
    if latest_year < stale_before:
        raise AssertionError(f"BLS annual history is stale: latest year {latest_year} < required {stale_before}")

    expected_count = latest_year - FIRST_YEAR + 1
    if len(records) != expected_count:
        raise AssertionError(f"non-contiguous annual record count: {len(records)} != {expected_count}")


def materialize_snapshot(payload: dict[str, Any], output_dir: Path, latest_path: Path | None) -> Path:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    latest_year = payload.get("latest_year")
    if not isinstance(latest_year, int):
        raise AssertionError(f"invalid latest year: {latest_year!r}")

    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / f"bls_nonfarm_business_labor_productivity_annual_{latest_year}_{digest[:12]}.json"
    artifact.write_text(serialized, encoding="utf-8")
    if latest_path is not None:
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(serialized, encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize BLS Nonfarm Business annual labor productivity from official Series Report HTML."
    )
    parser.add_argument("--percent-html", type=Path, required=True)
    parser.add_argument("--index-html", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--latest-path", type=Path)
    args = parser.parse_args()

    payload = build_payload(args.percent_html, args.index_html)
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
