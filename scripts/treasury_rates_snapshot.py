#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "investor2.us-treasury-yield-curves.v1"
OFFICIAL_URLS = {
    "nominal": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all?_format=csv&field_tdr_date_value={year}&page=&type=daily_treasury_yield_curve",
    "real": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all?_format=csv&field_tdr_date_value={year}&page=&type=daily_treasury_real_yield_curve",
}


def normalize_header(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not normalized:
        raise AssertionError(f"empty normalized header: {value!r}")
    return normalized


def parse_number(value: str) -> float | None:
    stripped = value.strip()
    if stripped in {"", "N/A", "NA"}:
        return None
    return float(stripped)


def parse_curve_csv(path: Path, curve: str) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or "Date" not in reader.fieldnames:
            raise AssertionError(f"Treasury CSV missing Date column: {path}")
        normalized_headers = [normalize_header(field) for field in reader.fieldnames]
        if len(normalized_headers) != len(set(normalized_headers)):
            raise AssertionError(f"Treasury CSV has duplicate normalized headers: {path}")

        records: list[dict[str, Any]] = []
        for raw in reader:
            record: dict[str, Any] = {
                "curve": curve,
                "date": datetime.strptime(raw["Date"].strip(), "%m/%d/%Y").date().isoformat(),
            }
            for field in reader.fieldnames:
                if field == "Date":
                    continue
                record[normalize_header(field)] = parse_number(raw[field])
            records.append(record)

    if not records:
        raise AssertionError(f"Treasury CSV has no records: {path}")
    records.sort(key=lambda item: item["date"])
    dates = [record["date"] for record in records]
    if len(dates) != len(set(dates)):
        raise AssertionError(f"Treasury CSV has duplicate dates: {path}")
    return records


def build_payload(nominal_csv: Path, real_csv: Path) -> dict[str, Any]:
    nominal = parse_curve_csv(nominal_csv, "nominal")
    real = parse_curve_csv(real_csv, "real")
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "U.S. Department of the Treasury",
        "source_urls": OFFICIAL_URLS,
        "latest_nominal_date": nominal[-1]["date"],
        "latest_real_date": real[-1]["date"],
        "records": nominal + real,
    }


def materialize_snapshot(payload: dict[str, Any], output_dir: Path, latest_path: Path | None) -> Path:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    latest_date = max(payload["latest_nominal_date"], payload["latest_real_date"])
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / f"us_treasury_yield_curves_{latest_date}_{digest[:12]}.json"
    artifact.write_text(serialized, encoding="utf-8")
    if latest_path is not None:
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(serialized, encoding="utf-8")
    return artifact


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize official U.S. Treasury nominal and real yield curves.")
    parser.add_argument("--nominal-csv", type=Path, required=True)
    parser.add_argument("--real-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--latest-path", type=Path)
    args = parser.parse_args()

    artifact = materialize_snapshot(
        build_payload(args.nominal_csv, args.real_csv),
        args.output_dir,
        args.latest_path,
    )
    try:
        print(artifact.relative_to(Path.cwd()).as_posix())
    except ValueError:
        print(artifact.as_posix())


if __name__ == "__main__":
    main()
