#!/usr/bin/env python3
"""Build deterministic ARK Big Ideas forecast comparison JSON and CSV views."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

THEMES = (
    "The Great Acceleration",
    "AI Infrastructure",
    "The AI Consumer Operating System",
    "AI Productivity",
    "Bitcoin",
    "Tokenized Assets",
    "DeFi Applications",
    "Multiomics",
    "Reusable Rockets",
    "Robotics",
    "Distributed Energy",
    "Autonomous Vehicles",
    "Autonomous Logistics",
)

CSV_FIELDS = (
    "theme",
    "forecast_id",
    "ark_claim_paraphrase",
    "baseline_value",
    "baseline_unit",
    "baseline_period",
    "target_value",
    "target_unit",
    "target_period",
    "scope",
    "comparison_status",
    "comparison_reason",
    "observed_series_id",
    "source_url",
    "source_page",
)


def comparison_forecast(forecast: dict[str, object]) -> dict[str, object]:
    comparison = forecast["comparison"]
    assert isinstance(comparison, dict)
    return {
        "forecast_id": forecast["forecast_id"],
        "ark_claim_paraphrase": forecast["ark_claim_paraphrase"],
        "baseline_value": forecast["baseline_value"],
        "baseline_unit": forecast["baseline_unit"],
        "baseline_period": forecast["baseline_period"],
        "target_value": forecast["target_value"],
        "target_unit": forecast["target_unit"],
        "target_period": forecast["target_period"],
        "scope": forecast["scope"],
        "comparison_status": comparison["status"],
        "comparison_reason": comparison["reason"],
        "observed_series_id": comparison["observed_series_id"],
        "source_url": forecast["source_url"],
        "source_page": forecast["source_page"],
    }


def build(catalog: dict[str, object]) -> dict[str, object]:
    forecasts = catalog["forecasts"]
    assert isinstance(forecasts, list)
    by_theme: dict[str, list[dict[str, object]]] = {theme: [] for theme in THEMES}
    for raw in forecasts:
        assert isinstance(raw, dict)
        theme = raw["theme"]
        assert isinstance(theme, str)
        if theme not in by_theme:
            raise ValueError(f"forecast uses unknown ARK Big Ideas theme: {theme}")
        by_theme[theme].append(comparison_forecast(raw))

    themes = []
    for theme in THEMES:
        rows = sorted(by_theme[theme], key=lambda row: str(row["forecast_id"]))
        themes.append({"theme": theme, "forecast_count": len(rows), "forecasts": rows})
    return {
        "schema_version": "investor2.ark-big-ideas-forecast-comparison.v1",
        "themes": themes,
    }


def write_json(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def write_csv(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        themes = payload["themes"]
        assert isinstance(themes, list)
        for theme_row in themes:
            assert isinstance(theme_row, dict)
            theme = str(theme_row["theme"])
            forecasts = theme_row["forecasts"]
            assert isinstance(forecasts, list)
            if not forecasts:
                writer.writerow({"theme": theme})
                continue
            for forecast in forecasts:
                assert isinstance(forecast, dict)
                writer.writerow({"theme": theme, **forecast})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("data/ark-big-ideas/forecast-catalog.json"),
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("api/v1/ark-big-ideas/forecast-comparison.json"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("api/v1/ark-big-ideas/forecast-comparison.csv"),
    )
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding="utf-8"))
    payload = build(catalog)
    write_json(payload, args.json_output)
    write_csv(payload, args.csv_output)


if __name__ == "__main__":
    main()
