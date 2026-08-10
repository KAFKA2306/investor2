from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Protocol

import pandas as pd
from pydantic import BaseModel, Field


class JQuantsClient(Protocol):
    def get_eq_bars_daily(
        self,
        code: str = "",
        from_yyyymmdd: str = "",
        to_yyyymmdd: str = "",
        date_yyyymmdd: str = "",
    ) -> pd.DataFrame: ...

    def get_eq_master(self, code: str = "", date: str = "") -> pd.DataFrame: ...

    def get_fin_summary_cursor(
        self,
        code: str = "",
        date_yyyymmdd: str = "",
        cursor: str = "",
    ) -> tuple[pd.DataFrame, str | None]: ...


class PipelineConfig(BaseModel):
    end_date: date
    lookback_days: int = Field(default=7, ge=1, le=31)
    output_dir: Path
    external_distribution_authorized: bool = False


class DatasetManifest(BaseModel):
    file: str
    rows: int = Field(ge=0)
    columns: list[str]
    sha256: str


class PipelineManifest(BaseModel):
    schema_version: str = "1"
    source: str = "J-Quants API v2"
    source_client: str = "J-Quants/jquants-api-client-python ClientV2"
    latest_market_date: str
    requested_window_start: str
    requested_window_end: str
    generated_at_utc: str
    external_distribution_authorized: bool
    publish_gate: str
    datasets: dict[str, DatasetManifest]


def _require_columns(name: str, frame: pd.DataFrame, required: set[str], *, allow_empty: bool = False) -> None:
    if frame.empty and not allow_empty:
        raise ValueError(f"{name}: empty dataset")
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing required columns: {sorted(missing)}")
    if not frame.empty:
        null_columns = [column for column in required if frame[column].isna().any()]
        if null_columns:
            raise ValueError(f"{name}: null values in required columns: {sorted(null_columns)}")


def _require_unique(name: str, frame: pd.DataFrame, key: list[str]) -> None:
    if frame.duplicated(key).any():
        raise ValueError(f"{name}: duplicate rows for key {key}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_dataset(output_dir: Path, name: str, frame: pd.DataFrame) -> DatasetManifest:
    path = output_dir / f"{name}.csv"
    frame.to_csv(path, index=False, lineterminator="\n")
    return DatasetManifest(file=path.name, rows=len(frame), columns=list(frame.columns), sha256=_sha256(path))


def fetch_validate_write(client: JQuantsClient, config: PipelineConfig) -> PipelineManifest:
    start_date = config.end_date - timedelta(days=config.lookback_days - 1)
    bars_window = client.get_eq_bars_daily(
        from_yyyymmdd=start_date.isoformat(),
        to_yyyymmdd=config.end_date.isoformat(),
    )
    _require_columns("equities_bars_daily", bars_window, {"Code", "Date"})

    parsed_dates = pd.to_datetime(bars_window["Date"], errors="raise")
    latest_timestamp = parsed_dates.max()
    latest_market_date = latest_timestamp.date()
    latest_mask = parsed_dates.dt.date == latest_market_date
    bars = bars_window.loc[latest_mask].copy()
    bars["Date"] = pd.to_datetime(bars["Date"], errors="raise").dt.strftime("%Y-%m-%d")
    _require_unique("equities_bars_daily", bars, ["Code", "Date"])
    bars.sort_values(["Code", "Date"], inplace=True)
    bars.reset_index(drop=True, inplace=True)

    latest_date_text = latest_market_date.isoformat()
    master = client.get_eq_master(date=latest_date_text)
    _require_columns("equities_master", master, {"Code"})
    _require_unique("equities_master", master, ["Code"])
    master.sort_values(["Code"], inplace=True)
    master.reset_index(drop=True, inplace=True)

    financials, _ = client.get_fin_summary_cursor(date_yyyymmdd=latest_date_text)
    if financials.empty:
        financials = pd.DataFrame(columns=["Code", "DiscDate"])
    _require_columns("financial_summary", financials, {"Code", "DiscDate"}, allow_empty=True)
    financial_sort = [column for column in ["DiscDate", "DiscTime", "Code"] if column in financials.columns]
    if financial_sort and not financials.empty:
        financials.sort_values(financial_sort, inplace=True)
        financials.reset_index(drop=True, inplace=True)

    config.output_dir.mkdir(parents=True, exist_ok=False)
    datasets = {
        "equities_master": _write_dataset(config.output_dir, "equities_master", master),
        "equities_bars_daily": _write_dataset(config.output_dir, "equities_bars_daily", bars),
        "financial_summary": _write_dataset(config.output_dir, "financial_summary", financials),
    }

    manifest = PipelineManifest(
        latest_market_date=latest_date_text,
        requested_window_start=start_date.isoformat(),
        requested_window_end=config.end_date.isoformat(),
        generated_at_utc=datetime.now(UTC).isoformat(),
        external_distribution_authorized=config.external_distribution_authorized,
        publish_gate="open" if config.external_distribution_authorized else "blocked",
        datasets=datasets,
    )
    (config.output_dir / "manifest.json").write_text(
        json.dumps(manifest.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _build_client() -> JQuantsClient:
    api_key = os.environ["JQUANTS_API_KEY"].strip()
    if not api_key:
        raise ValueError("JQUANTS_API_KEY is empty")

    import jquantsapi

    return jquantsapi.ClientV2(api_key=api_key)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and validate a narrow J-Quants API v2 snapshot.")
    parser.add_argument("--end-date", type=date.fromisoformat, required=True)
    parser.add_argument("--lookback-days", type=int, default=7)
    parser.add_argument("--output-dir", type=Path, default=Path(".jquants-staging"))
    parser.add_argument("--external-distribution-authorized", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config = PipelineConfig(
        end_date=args.end_date,
        lookback_days=args.lookback_days,
        output_dir=args.output_dir,
        external_distribution_authorized=args.external_distribution_authorized,
    )
    manifest = fetch_validate_write(_build_client(), config)
    print(manifest.model_dump_json())


if __name__ == "__main__":
    main()
