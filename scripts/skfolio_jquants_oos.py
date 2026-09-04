#!/usr/bin/env python3
"""Run frozen J-Quants OOS covariance comparisons for skfolio factor models."""

from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from skfolio.containers import AssetPanel

from scripts.jquants_japan_panel import choose_japan_universe, load_japan_inputs
from src.research.market_snapshot import MarketSnapshot, load_prices
from src.research.skfolio_characteristics import (
    asset_panel_from_prices,
    asset_panel_from_prices_and_market_cap,
    build_market_cap_characteristics_model,
    build_price_only_characteristics_model,
    market_cap_model_contract,
    model_contract,
)

ANNUALIZATION_FACTOR = 252.0
MIN_TRAIN_RETURN_OBSERVATIONS = 180
MIN_TEST_RETURN_OBSERVATIONS = 30
PRIMARY_METRICS = (
    "normalized_frobenius_error",
    "equal_weight_volatility_absolute_error",
)


@dataclass(frozen=True)
class Fold:
    index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compare empirical covariance, price-only CharacteristicsFactorModel, and "
            "true-MktCap Size/Beta CharacteristicsFactorModel on fixed PIT Japanese equities."
        )
    )
    parser.add_argument("--market-snapshot-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--market-regions", default="jp")
    parser.add_argument("--max-assets", type=int, default=64)
    parser.add_argument("--universe-cutoff", required=True)
    parser.add_argument("--evaluation-start", required=True)
    parser.add_argument("--evaluation-end", required=True)
    parser.add_argument("--train-months", type=int, default=12)
    parser.add_argument("--fold-months", type=int, default=3)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_array(array: np.ndarray) -> str:
    normalized = np.ascontiguousarray(np.asarray(array, dtype=np.float64))
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            {"shape": normalized.shape, "dtype": "float64"},
            separators=(",", ":"),
        ).encode()
    )
    digest.update(normalized.tobytes(order="C"))
    return digest.hexdigest()


def dataframe_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return json.loads(frame.reset_index().to_json(orient="records", date_format="iso"))


def build_walk_forward_folds(
    evaluation_start: pd.Timestamp,
    evaluation_end: pd.Timestamp,
    *,
    train_months: int,
    fold_months: int,
) -> list[Fold]:
    if evaluation_end < evaluation_start:
        raise ValueError("evaluation-end must be on/after evaluation-start")
    if train_months < 1 or fold_months < 1:
        raise ValueError("train-months and fold-months must be positive")

    folds: list[Fold] = []
    test_start = evaluation_start
    while test_start <= evaluation_end:
        test_end = min(
            test_start + pd.DateOffset(months=fold_months) - pd.Timedelta(days=1),
            evaluation_end,
        )
        folds.append(
            Fold(
                index=len(folds),
                train_start=test_start - pd.DateOffset(months=train_months),
                train_end=test_start - pd.Timedelta(days=1),
                test_start=test_start,
                test_end=test_end,
            )
        )
        test_start = test_end + pd.Timedelta(days=1)
    return folds


def covariance_error_metrics(
    predicted_covariance: np.ndarray,
    realized_covariance: np.ndarray,
) -> dict[str, float]:
    predicted = np.asarray(predicted_covariance, dtype=float)
    realized = np.asarray(realized_covariance, dtype=float)
    if (
        predicted.shape != realized.shape
        or predicted.ndim != 2
        or predicted.shape[0] != predicted.shape[1]
    ):
        raise ValueError("covariance matrices must be square and have identical shape")

    delta = predicted - realized
    realized_norm = float(np.linalg.norm(realized, ord="fro"))
    if realized_norm <= 0:
        raise ValueError("realized covariance Frobenius norm must be positive")

    n_assets = predicted.shape[0]
    weights = np.full(n_assets, 1.0 / n_assets)
    predicted_variance = float(weights @ predicted @ weights)
    realized_variance = float(weights @ realized @ weights)
    if predicted_variance < 0 or realized_variance < 0:
        raise ValueError("portfolio variance must be non-negative")

    predicted_vol = float(np.sqrt(predicted_variance * ANNUALIZATION_FACTOR))
    realized_vol = float(np.sqrt(realized_variance * ANNUALIZATION_FACTOR))
    return {
        "frobenius_error": float(np.linalg.norm(delta, ord="fro")),
        "normalized_frobenius_error": float(
            np.linalg.norm(delta, ord="fro") / realized_norm
        ),
        "diagonal_variance_mae": float(
            np.mean(np.abs(np.diag(predicted) - np.diag(realized)))
        ),
        "equal_weight_forecast_annualized_volatility": predicted_vol,
        "equal_weight_realized_annualized_volatility": realized_vol,
        "equal_weight_volatility_absolute_error": abs(predicted_vol - realized_vol),
    }


def canonical_frame_hash(frame: pd.DataFrame) -> str:
    serialized = frame.to_csv(
        index=True,
        date_format="%Y-%m-%d",
        float_format="%.12g",
        lineterminator="\n",
    )
    return sha256_text(serialized)


def returns_frame_from_panel(panel: AssetPanel) -> pd.DataFrame:
    return pd.DataFrame(
        panel["returns"],
        index=pd.DatetimeIndex(panel.observations),
        columns=[str(name) for name in panel.asset_names],
        dtype=float,
    )


def load_market_cap_matrix(
    snapshot_dir: Path,
    *,
    regions: list[str],
    selected_codes: list[str],
    index: pd.DatetimeIndex,
) -> pd.DataFrame:
    raw = load_prices(MarketSnapshot(snapshot_dir), regions=regions)
    if "MktCap" not in raw.columns:
        raise AssertionError("J-Quants snapshot prices do not contain true MktCap")
    code_column = "Code" if "Code" in raw.columns else "Ticker" if "Ticker" in raw.columns else None
    if code_column is None or "Date" not in raw.columns:
        raise AssertionError("J-Quants snapshot prices lack Code/Ticker or Date identity")

    caps = raw[[code_column, "Date", "MktCap"]].copy()
    caps = caps.rename(columns={code_column: "Code"})
    caps["Code"] = caps["Code"].astype(str)
    caps["Date"] = pd.to_datetime(caps["Date"], errors="raise").dt.tz_localize(None)
    caps["MktCap"] = pd.to_numeric(caps["MktCap"], errors="coerce")
    caps = caps[caps["Code"].isin(selected_codes)]
    duplicate = caps.duplicated(["Code", "Date"], keep=False)
    if duplicate.any():
        sample = caps.loc[duplicate, ["Code", "Date"]].head(5).to_dict(orient="records")
        raise AssertionError(f"duplicate selected Code/Date MktCap rows: {sample}")
    matrix = caps.pivot(index="Date", columns="Code", values="MktCap").sort_index()
    return matrix.reindex(index=index, columns=selected_codes)


def market_cap_coverage(frame: pd.DataFrame) -> dict[str, object]:
    values = frame.to_numpy(dtype=float, copy=True)
    total = int(values.size)
    finite_positive = np.isfinite(values) & (values > 0)
    valid = int(finite_positive.sum())
    complete_assets = int(finite_positive.all(axis=0).sum()) if values.size else 0
    return {
        "cells": total,
        "finite_positive_cells": valid,
        "invalid_cells": total - valid,
        "coverage": float(valid / total) if total else 0.0,
        "asset_count": int(frame.shape[1]),
        "assets_with_complete_coverage": complete_assets,
        "all_finite_positive": bool(total > 0 and finite_positive.all()),
    }


def run_fold(
    fold: Fold,
    prices: pd.DataFrame,
    market_cap: pd.DataFrame,
    output_dir: Path,
) -> dict[str, object]:
    train_prices = prices.loc[
        (prices.index >= fold.train_start) & (prices.index <= fold.train_end)
    ]
    if len(train_prices) < MIN_TRAIN_RETURN_OBSERVATIONS + 1:
        raise AssertionError(
            f"fold {fold.index} has only {len(train_prices)} training prices; "
            f"need at least {MIN_TRAIN_RETURN_OBSERVATIONS + 1}"
        )

    mask = pd.DataFrame(True, index=train_prices.index, columns=train_prices.columns)
    train_panel = asset_panel_from_prices(
        train_prices,
        active_mask=mask,
        estimation_mask=mask,
    )
    train_returns = returns_frame_from_panel(train_panel)
    if len(train_returns) < MIN_TRAIN_RETURN_OBSERVATIONS:
        raise AssertionError(f"fold {fold.index} has only {len(train_returns)} training returns")

    current_model = build_price_only_characteristics_model()
    with warnings.catch_warnings(record=True) as current_warnings:
        warnings.simplefilter("always")
        current_model.fit(X=train_returns, characteristics=train_panel)

    investment_universe = [str(name) for name in current_model.feature_names_in_]
    expected_universe = [str(name) for name in train_returns.columns]
    if investment_universe != expected_universe:
        raise AssertionError(
            f"fold {fold.index} skfolio investment universe differs from X.columns"
        )

    full_mask = pd.DataFrame(True, index=prices.index, columns=prices.columns)
    full_panel = asset_panel_from_prices(
        prices,
        active_mask=full_mask,
        estimation_mask=full_mask,
    )
    all_returns = returns_frame_from_panel(full_panel)
    test_returns = all_returns.loc[
        (all_returns.index >= fold.test_start) & (all_returns.index <= fold.test_end)
    ]
    if len(test_returns) < MIN_TEST_RETURN_OBSERVATIONS:
        raise AssertionError(
            f"fold {fold.index} has only {len(test_returns)} OOS return observations; "
            f"need at least {MIN_TEST_RETURN_OBSERVATIONS}"
        )
    if list(test_returns.columns) != investment_universe:
        raise AssertionError("OOS return columns do not match the explicit investment universe")

    baseline_covariance = train_returns.cov().to_numpy(dtype=float)
    current_covariance = np.asarray(
        current_model.return_distribution_.covariance,
        dtype=float,
    )
    realized_covariance = test_returns.cov().to_numpy(dtype=float)
    expected_shape = (len(investment_universe), len(investment_universe))
    for name, covariance in (
        ("baseline", baseline_covariance),
        ("current_skfolio", current_covariance),
        ("realized", realized_covariance),
    ):
        if covariance.shape != expected_shape or not np.isfinite(covariance).all():
            raise AssertionError(f"{name} covariance is not finite with shape {expected_shape}")

    current_factor_model = current_model.factor_model_
    if [str(name) for name in current_factor_model.asset_names] != investment_universe:
        raise AssertionError("current factor_model asset_names do not match investment universe")
    if current_factor_model.factor_returns is None or current_factor_model.exposures is None:
        raise AssertionError("current characteristics factor outputs are unexpectedly missing")

    baseline_metrics = covariance_error_metrics(baseline_covariance, realized_covariance)
    current_metrics = covariance_error_metrics(current_covariance, realized_covariance)

    train_market_cap = market_cap.loc[train_returns.index, train_returns.columns]
    coverage = market_cap_coverage(train_market_cap)
    candidate: dict[str, object]
    candidate_arrays: dict[str, np.ndarray] = {}
    if cast(bool, coverage["all_finite_positive"]):
        candidate_market_cap = market_cap.loc[train_prices.index, train_prices.columns]
        candidate_panel = asset_panel_from_prices_and_market_cap(
            train_prices,
            candidate_market_cap,
            active_mask=mask,
            estimation_mask=mask,
        )
        candidate_model = build_market_cap_characteristics_model()
        with warnings.catch_warnings(record=True) as candidate_warnings:
            warnings.simplefilter("always")
            candidate_model.fit(X=train_returns, characteristics=candidate_panel)
        if [str(name) for name in candidate_model.feature_names_in_] != investment_universe:
            raise AssertionError("MktCap candidate investment universe differs from baseline")
        candidate_covariance = np.asarray(
            candidate_model.return_distribution_.covariance,
            dtype=float,
        )
        if candidate_covariance.shape != expected_shape or not np.isfinite(candidate_covariance).all():
            raise AssertionError("MktCap candidate covariance is not finite with expected shape")
        candidate_factor_model = candidate_model.factor_model_
        if candidate_factor_model.factor_returns is None or candidate_factor_model.exposures is None:
            raise AssertionError("MktCap candidate factor outputs are unexpectedly missing")
        candidate_metrics = covariance_error_metrics(candidate_covariance, realized_covariance)
        candidate = {
            "status": "EVALUATED",
            "market_cap_coverage": coverage,
            "metrics": candidate_metrics,
            "delta_candidate_minus_baseline": {
                key: candidate_metrics[key] - baseline_metrics[key]
                for key in (
                    "frobenius_error",
                    "normalized_frobenius_error",
                    "diagonal_variance_mae",
                    "equal_weight_volatility_absolute_error",
                )
            },
            "model_warnings": sorted({str(item.message) for item in candidate_warnings}),
            "factor_diagnostics": dataframe_records(candidate_factor_model.summary()),
        }
        candidate_arrays = {
            "candidate_covariance": candidate_covariance,
            "candidate_factor_returns": np.asarray(candidate_factor_model.factor_returns, dtype=float),
            "candidate_exposures": np.asarray(candidate_factor_model.exposures, dtype=float),
            "candidate_loading_matrix": np.asarray(candidate_factor_model.loading_matrix, dtype=float),
            "candidate_idio_covariance": np.asarray(candidate_factor_model.idio_covariance, dtype=float),
        }
    else:
        candidate = {
            "status": "UNVERIFIED",
            "reason": "selected train-window true MktCap is not finite and strictly positive for every asset/date",
            "market_cap_coverage": coverage,
        }

    artifact_path = output_dir / f"fold{fold.index}.npz"
    np.savez_compressed(
        artifact_path,
        codes=np.asarray(investment_universe, dtype="U32"),
        current_factor_names=np.asarray(current_factor_model.factor_names, dtype="U64"),
        baseline_covariance=baseline_covariance,
        current_skfolio_covariance=current_covariance,
        realized_covariance=realized_covariance,
        current_factor_returns=np.asarray(current_factor_model.factor_returns, dtype=float),
        current_exposures=np.asarray(current_factor_model.exposures, dtype=float),
        current_loading_matrix=np.asarray(current_factor_model.loading_matrix, dtype=float),
        current_idio_covariance=np.asarray(current_factor_model.idio_covariance, dtype=float),
        **candidate_arrays,
    )

    return {
        "fold": {
            key: (str(value.date()) if isinstance(value, pd.Timestamp) else value)
            for key, value in asdict(fold).items()
        },
        "investment_universe_source": "CharacteristicsFactorModel.fit X.columns",
        "investment_universe": investment_universe,
        "observations": {
            "train_prices": int(len(train_prices)),
            "train_returns": int(len(train_returns)),
            "test_returns": int(len(test_returns)),
        },
        "baseline_empirical_covariance": baseline_metrics,
        "current_price_only_characteristics_covariance": current_metrics,
        "delta_current_minus_baseline": {
            key: current_metrics[key] - baseline_metrics[key]
            for key in (
                "frobenius_error",
                "normalized_frobenius_error",
                "diagonal_variance_mae",
                "equal_weight_volatility_absolute_error",
            )
        },
        "true_mktcap_size_beta_candidate": candidate,
        "output_hashes": {
            "baseline_covariance_sha256": sha256_array(baseline_covariance),
            "current_skfolio_covariance_sha256": sha256_array(current_covariance),
            "realized_covariance_sha256": sha256_array(realized_covariance),
            "npz_sha256": sha256_file(artifact_path),
            **{
                f"{name}_sha256": sha256_array(value)
                for name, value in candidate_arrays.items()
            },
        },
        "current_model_warnings": sorted({str(item.message) for item in current_warnings}),
        "current_factor_diagnostics": dataframe_records(current_factor_model.summary()),
    }


def _mean_metrics(
    folds: list[dict[str, object]],
    key: str,
) -> dict[str, float]:
    metric_names = (
        "frobenius_error",
        "normalized_frobenius_error",
        "diagonal_variance_mae",
        "equal_weight_volatility_absolute_error",
    )
    return {
        metric: float(
            np.mean([cast(dict[str, float], fold[key])[metric] for fold in folds])
        )
        for metric in metric_names
    }


def aggregate_results(folds: list[dict[str, object]]) -> dict[str, object]:
    baseline = _mean_metrics(folds, "baseline_empirical_covariance")
    current = _mean_metrics(folds, "current_price_only_characteristics_covariance")
    current_wins = {metric: current[metric] < baseline[metric] for metric in PRIMARY_METRICS}

    candidates = [cast(dict[str, object], fold["true_mktcap_size_beta_candidate"]) for fold in folds]
    if not all(candidate["status"] == "EVALUATED" for candidate in candidates):
        return {
            "mean_baseline_empirical_covariance": baseline,
            "mean_current_price_only_characteristics_covariance": current,
            "current_primary_metric_wins": current_wins,
            "true_mktcap_size_beta_candidate": {
                "status": "UNVERIFIED",
                "verdict": "UNVERIFIED",
                "reason": "true MktCap coverage failed in at least one training fold",
            },
        }

    candidate_metrics: dict[str, float] = {}
    for metric in (
        "frobenius_error",
        "normalized_frobenius_error",
        "diagonal_variance_mae",
        "equal_weight_volatility_absolute_error",
    ):
        candidate_metrics[metric] = float(
            np.mean(
                [cast(dict[str, float], cast(dict[str, object], candidate["metrics"]))[metric] for candidate in candidates]
            )
        )
    candidate_wins = {
        metric: candidate_metrics[metric] < baseline[metric] for metric in PRIMARY_METRICS
    }
    verdict = "USE" if all(candidate_wins.values()) else "REJECT"
    return {
        "mean_baseline_empirical_covariance": baseline,
        "mean_current_price_only_characteristics_covariance": current,
        "current_primary_metric_wins": current_wins,
        "true_mktcap_size_beta_candidate": {
            "status": "EVALUATED",
            "mean_metrics": candidate_metrics,
            "primary_metric_wins_vs_empirical": candidate_wins,
            "verdict": verdict,
        },
    }


def main() -> None:
    args = parse_args()
    evaluation_start = pd.Timestamp(args.evaluation_start)
    evaluation_end = pd.Timestamp(args.evaluation_end)
    cutoff = pd.Timestamp(args.universe_cutoff)
    folds = build_walk_forward_folds(
        evaluation_start,
        evaluation_end,
        train_months=args.train_months,
        fold_months=args.fold_months,
    )
    if len(folds) < 2:
        raise AssertionError("evaluation window must produce at least two OOS folds")

    load_args = argparse.Namespace(
        market_snapshot_dir=args.market_snapshot_dir,
        market_regions=args.market_regions,
        max_assets=args.max_assets,
    )
    prices_long, _, source_metadata = load_japan_inputs(load_args)
    selected_codes = sorted(choose_japan_universe(prices_long, cutoff, args.max_assets))
    selected = prices_long[prices_long["Code"].isin(selected_codes)].copy()
    price_matrix = (
        selected.pivot(index="Date", columns="Code", values="Close")
        .sort_index()
        .reindex(columns=selected_codes)
    )

    earliest_required = min(fold.train_start for fold in folds)
    working_prices = price_matrix.loc[
        (price_matrix.index >= earliest_required) & (price_matrix.index <= evaluation_end)
    ]
    incomplete_days = int(working_prices.isna().any(axis=1).sum())
    complete_prices = working_prices.dropna(axis=0, how="any")
    if complete_prices.empty:
        raise AssertionError("no complete selected-universe price observations")
    if list(complete_prices.columns) != selected_codes:
        raise AssertionError("price-matrix columns differ from fixed selected universe")
    if complete_prices.index.min() > earliest_required + pd.Timedelta(days=10):
        raise AssertionError("selected universe lacks the required training start history")
    if complete_prices.index.max() < evaluation_end - pd.Timedelta(days=10):
        raise AssertionError("selected universe lacks the required evaluation end history")

    regions = [value.strip().lower() for value in args.market_regions.split(",") if value.strip()]
    market_cap_matrix = load_market_cap_matrix(
        args.market_snapshot_dir,
        regions=regions,
        selected_codes=selected_codes,
        index=complete_prices.index,
    )
    overall_market_cap_coverage = market_cap_coverage(market_cap_matrix.iloc[1:])

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fold_results = [
        run_fold(fold, complete_prices, market_cap_matrix, args.output_dir) for fold in folds
    ]

    current_contract = model_contract()
    candidate_contract = market_cap_model_contract()
    contracts_json = json.dumps(
        {"current": current_contract, "candidate": candidate_contract},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    source_manifest = args.market_snapshot_dir / "manifest.json"
    universe_file = args.market_snapshot_dir / "universe.parquet"
    if not source_manifest.exists() or not universe_file.exists():
        raise FileNotFoundError("market snapshot must contain manifest.json and universe.parquet")

    summary = {
        "schema_version": "investor2.skfolio-mktcap-jquants-oos.v1",
        "execution_status": "completed",
        "source": source_metadata,
        "input_contract": {
            "source_manifest_sha256": sha256_file(source_manifest),
            "pit_universe_parquet_sha256": sha256_file(universe_file),
            "selected_price_panel_sha256": canonical_frame_hash(complete_prices),
            "selected_market_cap_panel_sha256": canonical_frame_hash(market_cap_matrix),
            "selected_market_cap_coverage": overall_market_cap_coverage,
            "market_cap_source_field": "J-Quants MktCap",
            "market_cap_fallback": "none",
            "selected_codes": selected_codes,
            "selected_asset_count": len(selected_codes),
            "universe_cutoff": str(cutoff.date()),
            "working_date_start": str(complete_prices.index.min().date()),
            "working_date_end": str(complete_prices.index.max().date()),
            "complete_calendar_days": int(len(complete_prices)),
            "dropped_incomplete_calendar_days": incomplete_days,
            "calendar_policy": (
                "intersection of dates with finite adjusted Close for every fixed selected asset; "
                "no forward/back fill"
            ),
        },
        "model_contracts": {
            "current_price_only": current_contract,
            "true_mktcap_size_beta": candidate_contract,
        },
        "model_contracts_sha256": sha256_text(contracts_json),
        "walk_forward_contract": {
            "train_months": args.train_months,
            "fold_months": args.fold_months,
            "evaluation_start": str(evaluation_start.date()),
            "evaluation_end": str(evaluation_end.date()),
            "fold_count": len(folds),
            "annualization_factor": ANNUALIZATION_FACTOR,
        },
        "baseline": "sample covariance of the same simple-return training observations",
        "current_candidate": "market + momentum + volatility, equal-weight characteristics model",
        "tested_candidate": (
            "market + EWMarketBeta + LogMarketCap using true J-Quants MktCap, "
            "market-cap benchmark and sqrt-market-cap regression weighting"
        ),
        "acceptance_rule": (
            "USE only if the true-MktCap candidate beats empirical covariance on both normalized "
            "Frobenius error and equal-weight volatility absolute error; otherwise REJECT; "
            "insufficient MktCap coverage is UNVERIFIED"
        ),
        "folds": fold_results,
        "aggregate": aggregate_results(fold_results),
        "claim_boundary": (
            "Risk/covariance forecast comparison only. This result does not establish alpha, "
            "expected-return, or strategy-performance improvement."
        ),
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact_manifest = {
        "schema_version": "investor2.skfolio-mktcap-jquants-oos-artifacts.v1",
        "summary_sha256": sha256_file(summary_path),
        "artifacts": {
            path.name: sha256_file(path) for path in sorted(args.output_dir.glob("fold*.npz"))
        },
        "input_hashes": {
            "source_manifest_sha256": summary["input_contract"]["source_manifest_sha256"],
            "pit_universe_parquet_sha256": summary["input_contract"]["pit_universe_parquet_sha256"],
            "selected_price_panel_sha256": summary["input_contract"]["selected_price_panel_sha256"],
            "selected_market_cap_panel_sha256": summary["input_contract"]["selected_market_cap_panel_sha256"],
            "model_contracts_sha256": summary["model_contracts_sha256"],
        },
    }
    manifest_path = args.output_dir / "artifact-manifest.json"
    manifest_path.write_text(
        json.dumps(artifact_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary["aggregate"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
