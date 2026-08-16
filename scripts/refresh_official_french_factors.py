#!/usr/bin/env python3
"""Pin current official Kenneth French FF3/FF5 monthly factors into OOS inputs.

The upstream current URLs are mutable. This script records SHA-256 for the raw ZIP,
extracted CSV, and normalized snapshot. Dataset identifiers remain stable for existing
research consumers; path, provenance, row count, and terminal month are authoritative.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs/research/paper_factor_registry.json"
SNAPSHOT = ROOT / "docs/research/kenneth_french_current_snapshot_2026-06.json"
REPORT_JSON = ROOT / "docs/research/official_current_paper_factor_suite.json"
PINNED_LAST_MONTH = "2026-06"

SPECS = {
    "ff3_1992_2020": {
        "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip",
        "definition": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html",
        "archive": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors_archive.html",
        "path": ROOT / "docs/research/data/ff3_1992_2026-06.csv",
        "start": "1992-07",
        "columns": {"SMB": "smb_percent", "HML": "hml_percent"},
    },
    "ff5_2015_2020": {
        "url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip",
        "definition": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3.html",
        "archive": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_5_factors_2x3_archive.html",
        "path": ROOT / "docs/research/data/ff5_2015_2026-06.csv",
        "start": "2015-05",
        "columns": {"RMW": "rmw_percent", "CMA": "cma_percent"},
    },
}


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def download(url: str) -> tuple[bytes, bytes, str]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "investor2-official-factor-refresh/1.0"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected exactly one CSV in {url}, got {members}")
        member = members[0]
        raw = archive.read(member)
    return payload, raw, member


def monthly_table(raw: bytes) -> tuple[list[str], list[list[str]]]:
    text = raw.decode("utf-8-sig", errors="strict")
    rows = list(csv.reader(io.StringIO(text)))
    header_at = None
    for index in range(len(rows) - 1):
        header = [cell.strip() for cell in rows[index]]
        next_row = [cell.strip() for cell in rows[index + 1]]
        if (
            header
            and header[0] == ""
            and "SMB" in header
            and next_row
            and len(next_row[0]) == 6
            and next_row[0].isdigit()
        ):
            header_at = index
            break
    if header_at is None:
        raise ValueError("monthly factor table not found")
    header = [cell.strip() for cell in rows[header_at]]
    monthly: list[list[str]] = []
    for row in rows[header_at + 1 :]:
        cells = [cell.strip() for cell in row]
        if not cells or len(cells[0]) != 6 or not cells[0].isdigit():
            break
        monthly.append(cells[: len(header)])
    if not monthly:
        raise ValueError("monthly factor table is empty")
    return header, monthly


def normalized_rows(
    header: list[str], rows: list[list[str]], spec: dict[str, object]
) -> list[list[str]]:
    positions = {name: header.index(name) for name in spec["columns"]}
    output: list[list[str]] = []
    for row in rows:
        yyyymm = row[0]
        month = f"{yyyymm[:4]}-{yyyymm[4:6]}"
        if month < spec["start"] or month > PINNED_LAST_MONTH:
            continue
        output.append(
            [f"{month}-01", *[row[positions[name]] for name in spec["columns"]]]
        )
    if not output:
        raise ValueError(f"no rows selected for {spec['path']}")
    if output[0][0][:7] != spec["start"]:
        raise ValueError(f"unexpected first month: {output[0][0]}")
    if output[-1][0][:7] != PINNED_LAST_MONTH:
        raise ValueError(f"official source does not reach pinned month {PINNED_LAST_MONTH}")
    months = [row[0][:7] for row in output]
    if months != sorted(months) or len(months) != len(set(months)):
        raise ValueError("selected months are not unique and chronological")
    return output


def write_csv(path: Path, spec: dict[str, object], rows: list[list[str]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["date", *spec["columns"].values()])
    writer.writerows(rows)
    content = buffer.getvalue()
    path.write_text(content, encoding="utf-8")
    return digest(content.encode("utf-8"))


def load_suite():
    path = ROOT / "scripts/verify_paper_factor_suite.py"
    spec = importlib.util.spec_from_file_location("verify_paper_factor_suite", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> None:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    manifest_datasets: dict[str, object] = {}
    current_datasets: dict[str, object] = {}

    for dataset_id, spec in SPECS.items():
        zip_payload, csv_payload, member = download(spec["url"])
        header, upstream_rows = monthly_table(csv_payload)
        rows = normalized_rows(header, upstream_rows, spec)
        normalized_sha = write_csv(spec["path"], spec, rows)
        current_datasets[dataset_id] = {
            "path": str(spec["path"].relative_to(ROOT)),
            "publisher": "Kenneth R. French Data Library",
            "authority": "official_primary",
            "source_url": spec["url"],
            "official_definition": spec["definition"],
            "official_archive": spec["archive"],
            "upstream_zip_sha256": digest(zip_payload),
            "upstream_csv_member": member,
            "upstream_csv_sha256": digest(csv_payload),
            "upstream_vintage": "current data library observed 2026-08-16; pinned through 2026-06",
            "crsp_input_format": "CIZ current-research-return generation",
            "identifier_note": "legacy stable dataset identifier; provenance and path define the current pinned vintage",
            "first_observation": rows[0][0][:7],
            "last_observation": rows[-1][0][:7],
            "rows": len(rows),
            "sha256": normalized_sha,
        }
        manifest_datasets[dataset_id] = {
            "source_url": spec["url"],
            "upstream_zip_sha256": digest(zip_payload),
            "upstream_csv_member": member,
            "upstream_csv_sha256": digest(csv_payload),
            "normalized_path": str(spec["path"].relative_to(ROOT)),
            "normalized_sha256": normalized_sha,
            "first_observation": rows[0][0][:7],
            "last_observation": rows[-1][0][:7],
            "rows": len(rows),
        }

    registry["datasets"] = current_datasets
    for study in registry["studies"]:
        if study["dataset"] in current_datasets:
            study["oos_end"] = PINNED_LAST_MONTH
    REGISTRY.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    for stale_path in (
        ROOT / "docs/research/data/ff3_1992_2020.csv",
        ROOT / "docs/research/data/ff5_2015_2020.csv",
        ROOT / "docs/research/official_current_paper_factor_suite.md",
    ):
        if stale_path.exists():
            stale_path.unlink()

    snapshot = {
        "schema_version": "investor2.kenneth-french-current-snapshot.v1",
        "publisher": "Kenneth R. French Data Library",
        "library_url": "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library.html",
        "retrieved_on": "2026-08-16",
        "pinned_last_observation": PINNED_LAST_MONTH,
        "authority": "official_primary",
        "generation_regime": {
            "current_release": "CIZ",
            "boundary": "Beginning with the January 2025 data release, the Data Library uses CRSP CIZ inputs for US research returns.",
            "legacy_fiz_archive_retained_separately": True,
            "do_not_mix_unlabeled_vintages": True,
        },
        "datasets": manifest_datasets,
    }
    SNAPSHOT.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    suite = load_suite()
    report = suite.build_report(REGISTRY)
    REPORT_JSON.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "dataset_rows": {
                    key: value["rows"] for key, value in current_datasets.items()
                },
                "last_observation": PINNED_LAST_MONTH,
                "study_verdicts": {
                    key: value["verdict"] for key, value in report["studies"].items()
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
