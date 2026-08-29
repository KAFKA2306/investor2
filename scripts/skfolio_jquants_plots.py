#!/usr/bin/env python3
"""Re-fit the frozen J-Quants folds and export skfolio's official FactorModel plots."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.jquants_japan_panel import load_japan_inputs
from scripts.skfolio_jquants_oos import canonical_price_hash, returns_frame_from_panel, sha256_array, sha256_file
from src.research.skfolio_characteristics import asset_panel_from_prices, build_price_only_characteristics_model
from src.research.skfolio_plot_exports import (
    export_factor_model_plots,
    export_oos_comparison_plots,
    write_plot_index,
    write_plot_manifest,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export skfolio FactorModel plots for the frozen J-Quants OOS evidence."
    )
    parser.add_argument("--market-snapshot-dir", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--market-regions", default="jp")
    return parser.parse_args()


def _load_summary(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError("summary must be a JSON object")
    if value.get("execution_status") != "completed":
        raise AssertionError("plotting requires a completed OOS evidence summary")
    return value


def _dict(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be an object")
    return value


def _list(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be an array")
    return value


def main() -> None:
    args = parse_args()
    summary = _load_summary(args.summary)
    input_contract = _dict(summary["input_contract"], "input_contract")
    selected_codes = [str(value) for value in _list(input_contract["selected_codes"], "selected_codes")]
    if not selected_codes:
        raise AssertionError("selected_codes is empty")

    load_args = argparse.Namespace(
        market_snapshot_dir=args.market_snapshot_dir,
        market_regions=args.market_regions,
        max_assets=len(selected_codes),
    )
    prices_long, _, _ = load_japan_inputs(load_args)
    selected = prices_long[prices_long["Code"].astype(str).isin(selected_codes)].copy()
    price_matrix = (
        selected.pivot(index="Date", columns="Code", values="Close").sort_index().reindex(columns=selected_codes)
    )
    working_start = pd.Timestamp(str(input_contract["working_date_start"]))
    working_end = pd.Timestamp(str(input_contract["working_date_end"]))
    complete_prices = price_matrix.loc[
        (price_matrix.index >= working_start) & (price_matrix.index <= working_end)
    ].dropna(axis=0, how="any")
    if list(complete_prices.columns) != selected_codes:
        raise AssertionError("plot price matrix columns differ from frozen selected_codes")
    expected_panel_hash = str(input_contract["selected_price_panel_sha256"])
    actual_panel_hash = canonical_price_hash(complete_prices)
    if actual_panel_hash != expected_panel_hash:
        raise AssertionError(
            "plot input does not match the frozen OOS selected price panel: "
            f"expected {expected_panel_hash}, got {actual_panel_hash}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, object]] = []
    folds = _list(summary["folds"], "folds")
    for fold_value in folds:
        fold_result = _dict(fold_value, "fold result")
        fold = _dict(fold_result["fold"], "fold")
        fold_index = int(fold["index"])
        train_start = pd.Timestamp(str(fold["train_start"]))
        train_end = pd.Timestamp(str(fold["train_end"]))
        train_prices = complete_prices.loc[
            (complete_prices.index >= train_start) & (complete_prices.index <= train_end)
        ]
        mask = pd.DataFrame(True, index=train_prices.index, columns=train_prices.columns)
        panel = asset_panel_from_prices(train_prices, active_mask=mask, estimation_mask=mask)
        train_returns = returns_frame_from_panel(panel)
        model = build_price_only_characteristics_model()
        model.fit(X=train_returns, characteristics=panel)

        expected_universe = [str(value) for value in _list(fold_result["investment_universe"], "investment_universe")]
        actual_universe = [str(value) for value in model.feature_names_in_]
        if actual_universe != expected_universe:
            raise AssertionError(f"fold {fold_index} investment universe differs from frozen evidence")

        factor_model = model.factor_model_
        output_hashes = _dict(fold_result["output_hashes"], "output_hashes")
        checks = {
            "skfolio_covariance_sha256": sha256_array(np.asarray(model.return_distribution_.covariance, dtype=float)),
            "factor_returns_sha256": sha256_array(np.asarray(factor_model.factor_returns, dtype=float)),
            "exposures_sha256": sha256_array(np.asarray(factor_model.exposures, dtype=float)),
        }
        for key, actual_hash in checks.items():
            expected_hash = str(output_hashes[key])
            if actual_hash != expected_hash:
                raise AssertionError(
                    f"fold {fold_index} {key} differs from frozen evidence: expected {expected_hash}, got {actual_hash}"
                )

        artifacts.extend(export_factor_model_plots(factor_model, args.output_dir, fold_index=fold_index))

    artifacts.extend(export_oos_comparison_plots(summary, args.output_dir))
    manifest_path = write_plot_manifest(
        args.output_dir,
        summary_sha256=sha256_file(args.summary),
        model_contract_sha256=str(summary["model_contract_sha256"]),
        artifacts=artifacts,
    )
    index_path = write_plot_index(args.output_dir, artifacts)
    print(
        json.dumps(
            {
                "plot_count": len(artifacts),
                "manifest": manifest_path.name,
                "index": index_path.name,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
