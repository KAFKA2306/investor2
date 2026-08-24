#!/usr/bin/env python3
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from scripts import alphazerobeta_japan_free_prepare as japan
from scripts import alphazerobeta_prepare as base
from src.research.tradability import tradability_summary


def main() -> None:
    args = base.parse_args()
    prices, benchmark, source_metadata = japan.load_japan_inputs(args)
    cutoff = pd.Timestamp(args.universe_cutoff)
    codes = japan.choose_japan_universe(prices, cutoff, args.max_assets)
    code_order = sorted(codes)

    selected = prices[prices["Code"].isin(codes)].copy()
    pieces: list[pd.DataFrame] = []
    for code, group in selected.groupby("Code", observed=True):
        feature_frame = base.build_asset_features(group).reset_index()
        feature_frame["Code"] = str(code)
        pieces.append(feature_frame)
    panel = pd.concat(pieces, ignore_index=True)
    if args.start:
        panel = panel[panel["Date"] >= pd.Timestamp(args.start)]
    if args.end:
        panel = panel[panel["Date"] <= pd.Timestamp(args.end)]

    feature_columns = [column for column in panel.columns if column not in {"Date", "Code", "asset_return"}]
    panel = base.cross_sectional_zscore(panel, feature_columns)

    bench = benchmark.dropna(subset=["BenchmarkReturn"]).copy()
    if args.start:
        bench = bench[bench["Date"] >= pd.Timestamp(args.start)]
    if args.end:
        bench = bench[bench["Date"] <= pd.Timestamp(args.end)]
    common_dates = pd.DatetimeIndex(bench["Date"].drop_duplicates().sort_values())
    if len(common_dates) < 252:
        raise AssertionError(f"only {len(common_dates)} benchmark trading days; need at least 252")

    dense_index = pd.MultiIndex.from_product([common_dates, code_order], names=["Date", "Code"])
    aligned = panel.set_index(["Date", "Code"]).sort_index().reindex(dense_index)
    tradable = aligned["asset_return"].notna().to_numpy(dtype=bool).reshape(len(common_dates), len(code_order))
    active_counts = tradable.sum(axis=1)
    keep = active_counts >= 2
    if not bool(keep.all()):
        kept_dates = common_dates[keep]
        dense_index = pd.MultiIndex.from_product([kept_dates, code_order], names=["Date", "Code"])
        aligned = aligned.reindex(dense_index)
        common_dates = kept_dates
        tradable = aligned["asset_return"].notna().to_numpy(dtype=bool).reshape(len(common_dates), len(code_order))

    feature_values = aligned[feature_columns].fillna(0.0).to_numpy(dtype=np.float32)
    features = feature_values.reshape(len(common_dates), len(code_order), len(feature_columns))
    returns = aligned["asset_return"].fillna(0.0).to_numpy(dtype=np.float32).reshape(len(common_dates), len(code_order))
    benchmark_returns = benchmark.set_index("Date").loc[common_dates, "BenchmarkReturn"].to_numpy(dtype=np.float32)

    if features.shape[:2] != tradable.shape or returns.shape != tradable.shape:
        raise AssertionError("dense panel arrays are not aligned")
    stats = tradability_summary(tradable)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        args.output,
        dates=np.asarray(common_dates.strftime("%Y-%m-%d"), dtype="U10"),
        codes=np.asarray(code_order, dtype="U32"),
        feature_names=np.asarray(feature_columns, dtype="U64"),
        features=features,
        returns=returns,
        benchmark=benchmark_returns,
        tradable=tradable,
    )

    manifest = args.manifest or args.output.with_suffix(args.output.suffix + ".manifest.json")
    base.write_json(
        manifest,
        {
            "schema_version": "investor2.alphazerobeta-prepared-dataset.v3",
            **source_metadata,
            "universe_cutoff": str(cutoff.date()),
            "selection_rule": "top mean pre-cutoff price*volume among PIT common stocks; no future-survivor filter",
            "selected_codes": code_order,
            "date_start": str(common_dates[0].date()),
            "date_end": str(common_dates[-1].date()),
            "trading_days": len(common_dates),
            "feature_names": feature_columns,
            "shape": {"T": int(features.shape[0]), "N": int(features.shape[1]), "F": int(features.shape[2])},
            "tradability": {
                **stats,
                "definition": "asset_return observed on the decision date for the cutoff-fixed universe",
                "inactive_feature_placeholder": 0.0,
                "inactive_return_placeholder": 0.0,
                "weight_rule": "non-tradable assets are forced to zero portfolio weight by downstream evaluators",
            },
            "dataset_sha256": base.sha256_file(args.output),
            "notes": [
                "Universe selection uses only data at or before universe_cutoff.",
                "The full cutoff-fixed universe is retained after cutoff; future survivors are not selected retrospectively.",
                "Missing, suspended, or delisted asset-days are represented by the tradable mask instead of deleting the whole market date.",
                "Zero feature/return values for inactive assets are tensor placeholders only; downstream policy and factor evaluation masks those assets.",
                "A position chosen while an asset is still tradable is not removed using next-day information; once the asset becomes non-tradable the next decision forces zero weight and turnover is charged.",
                "Features use backward-looking rolling windows and same-day cross-sectional normalization only.",
                "No backward fill is used.",
                "Materialized central cache inputs do not access Yahoo during panel preparation.",
            ],
        },
    )
    print(
        json.dumps(
            {
                "dataset": str(args.output),
                "manifest": str(manifest),
                "shape": list(features.shape),
                "tradability": stats,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
