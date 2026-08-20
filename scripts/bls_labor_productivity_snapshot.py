#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

SCHEMA_VERSION = "investor2.bls-nonfarm-business-labor-productivity-annual.v1"
SOURCE = "U.S. Bureau of Labor Statistics"
WORKBOOK_URL = "https://www.bls.gov/web/prod2/labor-productivity-major-sectors.xlsx"
OFFICIAL_URLS = {
    "workbook": WORKBOOK_URL,
    "tables": "https://www.bls.gov/productivity/tables/home.htm",
    "latest_release": "https://www.bls.gov/news.release/prod2.htm",
}
SECTOR = "Nonfarm business sector"
BASIS = "All workers"
MEASURE = "Labor productivity"
PERCENT_CHANGE_UNITS = "% Change from previous year"
ANNUAL_PERIOD = "Annual"
FIRST_YEAR = 1948
EXPECTED_HEADER = ["Sector", "Basis", "Measure", "Units", "Year", "Qtr", "Value"]
MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CELL_REF_RE = re.compile(r"^([A-Z]+)")


def column_index(cell_reference: str) -> int:
    match = CELL_REF_RE.match(cell_reference)
    if match is None:
        raise AssertionError(f"invalid XLSX cell reference: {cell_reference!r}")
    index = 0
    for letter in match.group(1):
        index = index * 26 + ord(letter) - ord("A") + 1
    return index - 1


def shared_strings(archive: ZipFile) -> list[str]:
    path = "xl/sharedStrings.xml"
    if path not in archive.namelist():
        return []
    root = ET.fromstring(archive.read(path))
    values: list[str] = []
    for item in root.findall(f"{{{MAIN_NS}}}si"):
        values.append("".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")))
    return values


def worksheet_path(archive: ZipFile, sheet_name: str) -> str:
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    relationship_id: str | None = None
    for sheet in workbook.findall(f".//{{{MAIN_NS}}}sheet"):
        if sheet.attrib.get("name") == sheet_name:
            relationship_id = sheet.attrib.get(f"{{{OFFICE_REL_NS}}}id")
            break
    if relationship_id is None:
        raise AssertionError(f"XLSX workbook missing sheet {sheet_name!r}")

    relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    target: str | None = None
    for relationship in relationships.findall(f"{{{PACKAGE_REL_NS}}}Relationship"):
        if relationship.attrib.get("Id") == relationship_id:
            target = relationship.attrib.get("Target")
            break
    if target is None:
        raise AssertionError(f"XLSX workbook missing relationship for sheet {sheet_name!r}")
    if target.startswith("/"):
        return target.lstrip("/")
    return f"xl/{target}"


def cell_text(cell: ET.Element, strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find(f"{{{MAIN_NS}}}v")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t"))
    if value_node is None or value_node.text is None:
        return ""
    if cell_type == "s":
        index = int(value_node.text)
        if index >= len(strings):
            raise AssertionError(f"XLSX shared-string index out of range: {index}")
        return strings[index]
    return value_node.text


def workbook_rows(workbook_path: Path, sheet_name: str = "MachineReadable") -> Iterator[list[str]]:
    with ZipFile(workbook_path) as archive:
        strings = shared_strings(archive)
        sheet_path = worksheet_path(archive, sheet_name)
        with archive.open(sheet_path) as sheet:
            for _, row in ET.iterparse(sheet, events=("end",)):
                if row.tag != f"{{{MAIN_NS}}}row":
                    continue
                values = [""] * len(EXPECTED_HEADER)
                for cell in row.findall(f"{{{MAIN_NS}}}c"):
                    reference = cell.attrib.get("r")
                    if reference is None:
                        raise AssertionError("XLSX cell is missing its reference")
                    index = column_index(reference)
                    if index < len(values):
                        values[index] = cell_text(cell, strings)
                yield values
                row.clear()


def add_observation(values: dict[int, float], year: int, raw_value: str, label: str) -> None:
    if raw_value in {"", "N.A."}:
        return
    if year in values:
        raise AssertionError(f"duplicate BLS annual observation: {label} {year}")
    values[year] = float(raw_value)


def build_payload(rows: Iterable[list[str]]) -> dict[str, object]:
    iterator = iter(rows)
    try:
        header = next(iterator)
    except StopIteration as exc:
        raise AssertionError("BLS workbook MachineReadable sheet is empty") from exc
    if header != EXPECTED_HEADER:
        raise AssertionError(f"unexpected BLS workbook header: {header!r}")

    percent_by_year: dict[int, float] = {}
    index_by_year: dict[int, float] = {}
    index_units: str | None = None

    for row in iterator:
        if row[0] != SECTOR or row[1] != BASIS or row[2] != MEASURE or row[5] != ANNUAL_PERIOD:
            continue
        year = int(row[4])
        units = row[3]
        if units == PERCENT_CHANGE_UNITS:
            add_observation(percent_by_year, year, row[6], "percent_change")
        elif units.startswith("Index ("):
            if index_units is not None and units != index_units:
                raise AssertionError(
                    f"multiple BLS labor-productivity index definitions found: {index_units!r}, {units!r}"
                )
            index_units = units
            add_observation(index_by_year, year, row[6], "index")

    if not percent_by_year:
        raise AssertionError("BLS workbook contains no annual labor-productivity percent-change observations")
    if not index_by_year or index_units is None:
        raise AssertionError("BLS workbook contains no annual labor-productivity index observations")

    percent_years = set(percent_by_year)
    missing_index = sorted(percent_years - set(index_by_year))
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
        "sector": SECTOR,
        "basis": BASIS,
        "measure": MEASURE,
        "frequency": "annual",
        "annual_period": ANNUAL_PERIOD,
        "percent_change_definition": PERCENT_CHANGE_UNITS,
        "index_definition": index_units,
        "first_year": years[0],
        "latest_year": years[-1],
        "records": records,
    }


def validate_historical_coverage(payload: dict[str, object]) -> None:
    first_year = payload.get("first_year")
    latest_year = payload.get("latest_year")
    records = payload.get("records")
    if first_year != FIRST_YEAR:
        raise AssertionError(f"unexpected first annual percent-change year: {first_year!r} != {FIRST_YEAR}")
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


def materialize_snapshot(payload: dict[str, object], output_dir: Path, latest_path: Path | None) -> Path:
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
        description="Materialize BLS Nonfarm Business annual labor productivity from the official XLSX workbook."
    )
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--latest-path", type=Path)
    args = parser.parse_args()

    payload = build_payload(workbook_rows(args.workbook))
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
