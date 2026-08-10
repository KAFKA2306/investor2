from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from scripts.jquants_hf_pipeline import PipelineConfig, fetch_validate_write


class FakeJQuantsClient:
    def __init__(self, *, missing_bar_code: bool = False) -> None:
        self.missing_bar_code = missing_bar_code

    def get_eq_bars_daily(
        self,
        code: str = "",
        from_yyyymmdd: str = "",
        to_yyyymmdd: str = "",
        date_yyyymmdd: str = "",
    ) -> pd.DataFrame:
        rows = pd.DataFrame(
            [
                {"Code": "13010", "Date": "2026-08-06", "C": 100.0, "Vo": 10_000},
                {"Code": "13050", "Date": "2026-08-06", "C": 200.0, "Vo": 20_000},
                {"Code": "13010", "Date": "2026-08-07", "C": 101.0, "Vo": 11_000},
                {"Code": "13050", "Date": "2026-08-07", "C": 202.0, "Vo": 21_000},
            ]
        )
        if self.missing_bar_code:
            rows.drop(columns=["Code"], inplace=True)
        return rows

    def get_eq_master(self, code: str = "", date: str = "") -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"Code": "13010", "CoName": "Alpha"},
                {"Code": "13050", "CoName": "Beta"},
            ]
        )

    def get_fin_summary_cursor(
        self,
        code: str = "",
        date_yyyymmdd: str = "",
        cursor: str = "",
    ) -> tuple[pd.DataFrame, str | None]:
        return pd.DataFrame([{"Code": "13010", "DiscDate": "2026-08-07", "Sales": 1000}]), None


def test_pipeline_keeps_latest_market_date_and_blocks_publish_by_default(tmp_path: Path) -> None:
    output_dir = tmp_path / "snapshot"
    manifest = fetch_validate_write(
        FakeJQuantsClient(),
        PipelineConfig(end_date=date(2026, 8, 9), lookback_days=7, output_dir=output_dir),
    )

    bars = pd.read_csv(output_dir / "equities_bars_daily.csv", dtype={"Code": str})
    assert manifest.latest_market_date == "2026-08-07"
    assert manifest.publish_gate == "blocked"
    assert manifest.external_distribution_authorized is False
    assert len(bars) == 2
    assert set(bars["Date"]) == {"2026-08-07"}
    assert (output_dir / "manifest.json").is_file()


def test_distribution_gate_can_only_be_opened_explicitly(tmp_path: Path) -> None:
    manifest = fetch_validate_write(
        FakeJQuantsClient(),
        PipelineConfig(
            end_date=date(2026, 8, 9),
            lookback_days=7,
            output_dir=tmp_path / "snapshot",
            external_distribution_authorized=True,
        ),
    )

    assert manifest.publish_gate == "open"
    assert manifest.external_distribution_authorized is True


def test_missing_required_boundary_column_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        fetch_validate_write(
            FakeJQuantsClient(missing_bar_code=True),
            PipelineConfig(end_date=date(2026, 8, 9), lookback_days=7, output_dir=tmp_path / "snapshot"),
        )
