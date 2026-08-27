#!/usr/bin/env python3
"""Run a frozen J-Quants OOS covariance comparison for skfolio CharacteristicsFactorModel."""

from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from scripts.jquants_japan_panel import choose_japan_universe, load_japan_inputs
from src.research.skfolio_characteristics import (
    asset_panel_from_prices,
    build_price_only_characteristics_model,
    model_contract,
)

ANNUALIZATION_FACTOR = 252.0
MIN_TRAIN_RETURN_OBSERVATIONS = 180
MIN_TEST_RETURN_OBSERVATIONS = 30


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
            "Compare empirical covariance with skfolio CharacteristicsFactorModel "
            "on fixed PIT Japanese equities and walk-forward OOS folds."
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
    digest.update(json.dumps({"shape": normalized.shape, "dtype": "float64"}, separators=(",", ":")).encode())
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
    if predicted.shape != realized.shape or predicted.ndim != 2 or predicted.shape[0] != predicted.shape[1]:
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
        "normalized_frobenius_error": float(np.linalg.norm(delta, ord="fro") / realized_norm),
        "diagonal_variance_mae": float(np.mean(np.abs(np.diag(predicted) - np.diag(realized)))),
        "equal_weight_forecast_annualized_volatility": predicted_vol,
        "equal_weight_realized_annualized_volatility": realized_vol,
        "equal_weight_volatility_absolute_error": abs(predicted_vol - realized_vol),
    }


def canonical_price_hash(prices: pd.DataFrame) -> str:
    serialized = prices.to_csv(
        index=True,
        date_format="%Y-%m-%d",
        float_format="%.12g",
        lineterminator="\n",
    )
    return sha256_text(serialized)


def returns_frame_from_panel(panel) -> pd.DataFrame:
    return pd.DataFrame(
        panel["returns"],
        index=pd.DatetimeIndex(panel.observations),
        columns=[str(name) for name in panel.asset_names],
        dtype=float,
    )


def run_fold(fold: Fold, prices: pd.DataFrame, output_dir: Path) -> dict[str, object]:
    train_prices = prices.loc[(prices.index >= fold.train_start) & (prices.index <= fold.train_end)]
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

    model = build_price_only_characteristics_model()
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        model.fit(X=train_returns, characteristics=train_panel)

    investment_universe = [str(name) for name in model.feature_names_in_]
    expected_universe = [str(name) for name in train_returns.columns]
    if investment_universe != expected_universe:
        raise AssertionError(f"fold {fold.index} skfolio investment universe differs from X.columns")

    full_mask = pd.DataFrame(True, index=prices.index, columns=prices.columns)
    full_panel = asset_panel_from_prices(prices, active_mask=full_mask, estimation_mask=full_mask)
    all_returns = returns_frame_from_panel(full_panel)
    test_returns = all_returns.loc[(all_returns.index >= fold.test_start) & (all_returns.index <= fold.test_end)]
    if len(test_returns) < MIN_TEST_RETURN_OBSERVATIONS:
        raise AssertionError(
            f"fold {fold.index} has only {len(test_returns)} OOS return observations; "
            f"need at least {MIN_TEST_RETURN_OBSERVATIONS}"
        )
    if list(test_returns.columns) != investment_universe:
        raise AssertionError("OOS return columns do not match the explicit investment universe")

    baseline_covariance = train_returns.cov().to_numpy(dtype=float)
    skfolio_covariance = np.asarray(model.return_distribution_.covariance, dtype=float)
    realized_covariance = test_returns.cov().to_numpy(dtype=float)
    expected_shape = (len(investment_universe), len(investment_universe))
    for name, covariance in (
        ("baseline", baseline_covariance),
        ("skfolio", skfolio_covariance),
        ("realized", realized_covariance),
    ):
        if covariance.shape != expected_shape or not np.isfinite(covariance).all():
            raise AssertionError(f"{name} covariance is not finite with shape {expected_shape}")

    factor_model = model.factor_model_
    if [str(name) for name in factor_model.asset_names] != investment_universe:
        raise AssertionError("factor_model asset_names do not match explicit investment universe")
    if factor_model.factor_returns is None or factor_model.exposures is None:
        raise AssertionError("characteristics factor outputs are unexpectedly missing")

    baseline_metrics = covariance_error_metrics(baseline_covariance, realized_covariance)
    skfolio_metrics = covariance_error_metrics(skfolio_covariance, realized_covariance)

    artifact_path = output_dir / f"fold{fold.index}.npz"
    np.savez_compressed(
        artifact_path,
        codes=np.asarray(investment_universe, dtype="U32"),
        factor_names=np.asarray(factor_model.factor_names, dtype="U64"),
        baseline_covariance=baseline_covariance,
        skfolio_covariance=skfolio_covariance,
        realized_covariance=realized_covariance,
        factor_returns=np.asarray(factor_model.factor_returns, dtype=float),
        exposures=np.asarray(factor_model.exposures, dtype=float),
        loading_matrix=np.asarray(factor_model.loading_matrix, dtype=float),
        idio_covariance=np.asarray(factor_model.idio_covariance, dtype=float),
    )

    diagnostics = dataframe_records(factor_model.summary())
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
        "skfolio_characteristics_covariance": skfolio_metrics,
        "delta_skfolio_minus_baseline": {
            key: skfolio_metrics[key] - baseline_metrics[key]
            for key in (
                "frobenius_error",
                "normalized_frobenius_error",
                "diagonal_variance_mae",
                "equal_weight_volatility_absolute_error",
            )
        },
        "output_hashes": {
            "baseline_covariance_sha256": sha256_array(baseline_covariance),
            "skfolio_covariance_sha256": sha256_array(skfolio_covariance),
            "realized_covariance_sha256": sha256_array(realized_covariance),
            "factor_returns_sha256": sha256_array(np.asarray(factor_model.factor_returns, dtype=float)),
            "exposures_sha256": sha256_array(np.asarray(factor_model.exposures, dtype=float)),
            "loading_matrix_sha256": sha256_array(np.asarray(factor_model.loading_matrix, dtype=float)),
            "idio_covariance_sha256": sha256_array(np.asarray(factor_model.idio_covariance, dtype=float)),
            "npz_sha256": sha256_file(artifact_path),
        },
        "model_warnings": sorted({str(item.message) for item in caught_warnings}),
        "factor_diagnostics": diagnostics,
    }


def aggregate_results(folds: list[dict[str, object]]) -> dict[str, object]:
    metric_names = (
        "frobenius_error",
        "normalized_frobenius_error",
        "diagonal_variance_mae",
        "equal_weight_volatility_absolute_error",
    )
    baseline: dict[str, float] = {}
    candidate: dict[str, float] = {}
    delta: dict[str, float] = {}
    for metric in metric_names:
        baseline[metric] = float(np.mean([fold["baseline_empirical_covariance"][metric] for fold in folds]))
        candidate[metric] = float(
            np.mean([fold["skfolio_characteristics_covariance"][metric] for fold in folds])
        )
        delta[metric] = candidate[metric] - baseline[metric]

    direct_wins = {
        "normalized_frobenius_error": (
            candidate["normalized_frobenius_error"] < baseline["normalized_frobenius_error"]
        ),
        "equal_weight_volatility_absolute_error": (
            candidate["equal_weight_volatility_absolute_error"]
            < baseline["equal_weight_volatility_absolute_error"]
        ),
    }
    if all(direct_wins.values()):
        verdict = "skfolio_better_on_both_primary_risk_metrics"
    elif any(direct_wins.values()):
        verdict = "mixed"
    else:
        verdict = "empirical_baseline_better_or_equal_on_both_primary_risk_metrics"

    return {
        "mean_baseline_empirical_covariance": baseline,
        "mean_skfolio_characteristics_covariance": candidate,
        "mean_delta_skfolio_minus_baseline": delta,
        "primary_metric_wins": direct_wins,
        "verdict": verdict,
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
    price_matrix = selected.pivot(index="Date", columns="Code", values="Close").sort_index().reindex(columns=selected_codes)

    earliest_required = min(fold.train_start for fold in folds)
    working_prices = price_matrix.loc[(price_matrix.index >= earliest_required) & (price_matrix.index <= evaluation_end)]
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

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fold_results = [run_fold(fold, complete_prices, args.output_dir) for fold in folds]

    contract = model_contract()
    contract_json = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source_manifest = args.market_snapshot_dir / "manifest.json"
    universe_file = args.market_snapshot_dir / "universe.parquet"
    if not source_manifest.exists() or not universe_file.exists():
        raise FileNotFoundError("market snapshot must contain manifest.json and universe.parquet")

    summary = {
        "schema_version": "investor2.skfolio-characteristics-jquants-oos.v1",
        "execution_status": "completed",
        "source": source_metadata,
        "input_contract": {
            "source_manifest_sha256": sha256_file(source_manifest),
            "pit_universe_parquet_sha256": sha256_file(universe_file),
            "selected_price_panel_sha256": canonical_price_hash(complete_prices),
            "selected_codes": selected_codes,
            "selected_asset_count": len(selected_codes),
            "universe_cutoff": str(cutoff.date()),
            "working_date_start": str(complete_prices.index.min().date()),
            "working_date_end": str(complete_prices.index.max().date()),
            "complete_calendar_days": int(len(complete_prices)),
            "dropped_incomplete_calendar_days": incomplete_days,
            "calendar_policy": (
                "intersection of dates with finite adjusted Close for every fixed selected asset; no forward/back fill"
            ),
        },
        "model_contract": contract,
        "model_contract_sha256": sha256_text(contract_json),
        "walk_forward_contract": {
            "train_months": args.train_months,
            "fold_months": args.fold_months,
            "evaluation_start": str(evaluation_start.date()),
            "evaluation_end": str(evaluation_end.date()),
            "fold_count": len(folds),
            "annualization_factor": ANNUALIZATION_FACTOR,
        },
        "baseline": "sample covariance of the same simple-return training observations",
        "candidate": "skfolio CharacteristicsFactorModel return_distribution_.covariance",
        "folds": fold_results,
        "aggregate": aggregate_results(fold_results),
        "claim_boundary": (
            "Risk/covariance forecast comparison only. This result does not establish alpha, expected-return, "
            "or strategy-performance improvement."
        ),
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifact_manifest = {
        "schema_version": "investor2.skfolio-characteristics-jquants-oos-artifacts.v1",
        "summary_sha256": sha256_file(summary_path),
        "artifacts": {path.name: sha256_file(path) for path in sorted(args.output_dir.glob("fold*.npz"))},
        "input_hashes": {
            "source_manifest_sha256": summary["input_contract"]["source_manifest_sha256"],
            "pit_universe_parquet_sha256": summary["input_contract"]["pit_universe_parquet_sha256"],
            "selected_price_panel_sha256": summary["input_contract"]["selected_price_panel_sha256"],
            "model_contract_sha256": summary["model_contract_sha256"],
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
