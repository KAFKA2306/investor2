from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.bls_labor_productivity_snapshot import (
    EXPECTED_DATA_HEADER,
    EXPECTED_MEASURE,
    EXPECTED_PERCENT_DURATION,
    EXPECTED_SECTOR,
    SERIES_IDS,
    build_payload,
    materialize_snapshot,
)


def write_series_report(
    path: Path,
    *,
    series_id: str,
    duration: str,
    annual_values: list[tuple[int, str]],
) -> None:
    catalog_rows = {
        "Series Id": series_id,
        "Sector": EXPECTED_SECTOR,
        "Measure": EXPECTED_MEASURE,
        "Duration": duration,
    }
    catalog = "".join(f"<tr><th>{key}:</th><td>{value}</td></tr>" for key, value in catalog_rows.items())
    header = "".join(f"<th>{cell}</th>" for cell in EXPECTED_DATA_HEADER)
    rows = "".join(
        "<tr>"
        f"<th>{year}</th>"
        "<td>1.0</td><td>1.0</td><td>1.0</td><td>1.0</td>"
        f"<td>{annual}</td>"
        "</tr>"
        for year, annual in annual_values
    )
    path.write_text(
        "<html><body>"
        f'<table id="catalog1" class="catalog">{catalog}</table>'
        f'<table id="table1" class="regular-data"><tr>{header}</tr>{rows}</table>'
        "</body></html>",
        encoding="utf-8",
    )


class BlsLaborProductivitySnapshotTest(unittest.TestCase):
    def test_extracts_official_annual_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            percent = root / "percent.html"
            index = root / "index.html"
            write_series_report(
                percent,
                series_id=SERIES_IDS["percent_change"],
                duration=EXPECTED_PERCENT_DURATION,
                annual_values=[(2024, "3.0"), (2025, "2.1")],
            )
            write_series_report(
                index,
                series_id=SERIES_IDS["index"],
                duration="Index",
                annual_values=[(2024, "115.366"), (2025, "117.785")],
            )

            payload = build_payload(percent, index)

        self.assertEqual(payload["first_year"], 2024)
        self.assertEqual(payload["latest_year"], 2025)
        self.assertEqual(
            payload["records"],
            [
                {"year": 2024, "percent_change": 3.0, "index": 115.366},
                {"year": 2025, "percent_change": 2.1, "index": 117.785},
            ],
        )

    def test_fails_closed_when_index_history_is_incomplete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            percent = root / "percent.html"
            index = root / "index.html"
            write_series_report(
                percent,
                series_id=SERIES_IDS["percent_change"],
                duration=EXPECTED_PERCENT_DURATION,
                annual_values=[(2024, "3.0"), (2025, "2.1")],
            )
            write_series_report(
                index,
                series_id=SERIES_IDS["index"],
                duration="Index",
                annual_values=[(2025, "117.785")],
            )

            with self.assertRaisesRegex(AssertionError, r"missing index years=\[2024\]"):
                build_payload(percent, index)

    def test_rejects_wrong_series_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            percent = root / "percent.html"
            index = root / "index.html"
            write_series_report(
                percent,
                series_id="PRS00000000",
                duration=EXPECTED_PERCENT_DURATION,
                annual_values=[(2025, "2.1")],
            )
            write_series_report(
                index,
                series_id=SERIES_IDS["index"],
                duration="Index",
                annual_values=[(2025, "117.785")],
            )

            with self.assertRaisesRegex(AssertionError, "unexpected BLS series id"):
                build_payload(percent, index)

    def test_materialized_filename_is_content_addressed(self) -> None:
        payload: dict[str, object] = {
            "schema_version": "investor2.bls-nonfarm-business-labor-productivity-annual.v1",
            "source": "U.S. Bureau of Labor Statistics",
            "latest_year": 2025,
            "records": [{"year": 2025, "percent_change": 2.1, "index": 117.785}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latest = root / "latest.json"
            artifact = materialize_snapshot(payload, root / "snapshots", latest)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            expected_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]
            self.assertEqual(
                artifact.name,
                f"bls_nonfarm_business_labor_productivity_annual_2025_{expected_hash}.json",
            )
            self.assertEqual(latest.read_text(encoding="utf-8"), serialized)


if __name__ == "__main__":
    unittest.main()
