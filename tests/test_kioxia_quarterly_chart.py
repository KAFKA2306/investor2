from __future__ import annotations

import json
from pathlib import Path

from scripts.kioxia_quarterly_chart import DEFAULT_INPUT, build_page, load_kioxia_series


def test_kioxia_series_excludes_unverified_fy2027_q1() -> None:
    payload, rows = load_kioxia_series(DEFAULT_INPUT)
    assert payload["company_count"] == 50
    assert len(rows) == 8
    assert (rows[0]["fiscal_year"], rows[0]["quarter"]) == (2025, 1)
    assert (rows[-1]["fiscal_year"], rows[-1]["quarter"]) == (2026, 4)
    assert all(row["fiscal_year"] <= 2026 for row in rows)
    assert all(row.get("revenue") is not None for row in rows)


def test_kioxia_chart_builds_page_and_summary(tmp_path: Path) -> None:
    payload, rows = load_kioxia_series(DEFAULT_INPUT)
    build_page(payload, rows, tmp_path)

    assert (tmp_path / "chart.png").stat().st_size > 0
    assert (tmp_path / "index.html").stat().st_size > 0
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    assert summary["edinet_code"] == "E35948"
    assert summary["point_count"] == 8
    assert summary["first_period"] == "FY2025 Q1"
    assert summary["last_period"] == "FY2026 Q4"
    assert summary["excluded_periods"][0]["period"] == "FY2027 Q1"
