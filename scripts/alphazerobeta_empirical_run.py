#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import traceback
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.research.alphazerobeta import write_json

CANDIDATE_ETFS = ("QQQ", "IWM", "DIA", "TLT", "GLD", "XLF", "XLK", "XLE", "XLV", "XLI", "XLP", "XLY")
BENCHMARK = "SPY"
MARKET_DATA_PROVIDER = "yahoo_chart"
SOURCE_START = "2020-01-01"
SOURCE_END = "2024-12-31"
UNIVERSE_CUTOFF = "2023-06-30"
TEST_START = "2024-01-01"
TEST_END = "2024-12-31"
MAX_ASSETS = 8
SEED = 2306
ITERATIONS = 4
HORIZON = 60
HIDDEN_SIZE = 64
PRIMARY_LAMBDA_CORR = 0.5
ABLATION_LAMBDA_CORR = 0.0
PRIMARY_TRANSACTION_COST_BPS = 15.0
PRIMARY_BORROW_FEE_BPS = 100.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bounded, reproducible AlphaZeroBeta 2024 OOS validation.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/research/results/alphazerobeta_2024"))
    return parser.parse_args()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; investor2-research/1.0; +https://github.com/KAFKA2306/investor2)"
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    if not payload:
        raise RuntimeError(f"empty response from {url}")
    return payload


def download_daily(symbol: str) -> tuple[pd.DataFrame, dict[str, object]]:
    start_epoch = int(pd.Timestamp(SOURCE_START, tz="UTC").timestamp())
    end_epoch = int((pd.Timestamp(SOURCE_END, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    query = urllib.parse.urlencode(
        {
            "period1": start_epoch,
            "period2": end_epoch,
            "interval": "1d",
            "events": "history",
            "includeAdjustedClose": "true",
        }
    )
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{query}"
    payload = fetch_bytes(url)
    document = json.loads(payload)
    result = document.get("chart", {}).get("result")
    if not result:
        raise RuntimeError(f"Yahoo chart returned no result for {symbol}: {document.get('chart', {}).get('error')}")
    node = result[0]
    timestamps = node["timestamp"]
    quote = node["indicators"]["quote"][0]
    adjusted = node.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose")
    closes = adjusted if adjusted is not None else quote["close"]
    frame = pd.DataFrame(
        {
            "Date": pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None).normalize(),
            "Close": closes,
            "Volume": quote["volume"],
        }
    ).dropna()
    frame["Close"] = pd.to_numeric(frame["Close"], errors="raise")
    frame["Volume"] = pd.to_numeric(frame["Volume"], errors="raise")
    if len(frame) < 1000:
        raise RuntimeError(f"Yahoo returned only {len(frame)} daily rows for {symbol}")
    return frame.sort_values("Date").reset_index(drop=True), {
        "symbol": symbol,
        "provider": MARKET_DATA_PROVIDER,
        "url": url,
        "raw_sha256": sha256_bytes(payload),
        "row_count": int(len(frame)),
        "date_start": str(frame["Date"].iloc[0].date()),
        "date_end": str(frame["Date"].iloc[-1].date()),
        "price_field": "adjusted_close_when_available",
    }


def run(command: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True, env=env)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_market_inputs(output_dir: Path) -> tuple[Path, Path, Path]:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    source_records: list[dict[str, object]] = []
    asset_frames: list[pd.DataFrame] = []
    for symbol in CANDIDATE_ETFS:
        frame, record = download_daily(symbol)
        frame.insert(0, "Code", symbol)
        asset_frames.append(frame[["Code", "Date", "Close", "Volume"]])
        source_records.append(record)
    benchmark, benchmark_record = download_daily(BENCHMARK)
    source_records.append(benchmark_record)

    prices = pd.concat(asset_frames, ignore_index=True).sort_values(["Code", "Date"])
    prices_path = raw_dir / "prices.csv"
    benchmark_path = raw_dir / "benchmark.csv"
    prices.to_csv(prices_path, index=False, date_format="%Y-%m-%d")
    benchmark[["Date", "Close"]].to_csv(benchmark_path, index=False, date_format="%Y-%m-%d")

    source_manifest = output_dir / "source_manifest.json"
    write_json(
        source_manifest,
        {
            "schema_version": "investor2.alphazerobeta-market-source-snapshot.v1",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "provider_contract": MARKET_DATA_PROVIDER,
            "candidate_universe": list(CANDIDATE_ETFS),
            "candidate_universe_contract": (
                "Fixed broad/sector ETF candidate set declared before OOS outcomes are observed; all instruments predate the "
                "2020-2024 sample. Final assets are selected only by pre-cutoff mean dollar volume. This is a bounded "
                "fixed-universe mechanism validation, not an exhaustive investable-universe claim."
            ),
            "benchmark": BENCHMARK,
            "source_window": {"start": SOURCE_START, "end": SOURCE_END},
            "records": source_records,
            "normalized_prices_sha256": sha256_file(prices_path),
            "normalized_benchmark_sha256": sha256_file(benchmark_path),
        },
    )
    return prices_path, benchmark_path, source_manifest


def train_pair(output_dir: Path, dataset_path: Path, fold_index: int) -> tuple[Path, Path]:
    primary = output_dir / f"primary_fold{fold_index}.json"
    ablation = output_dir / f"ablation_fold{fold_index}.json"
    common = [
        sys.executable,
        "scripts/alphazerobeta_train.py",
        "--dataset",
        str(dataset_path),
        "--test-start",
        TEST_START,
        "--test-end",
        TEST_END,
        "--fold-index",
        str(fold_index),
        "--device",
        "cpu",
        "--seed",
        str(SEED),
        "--iterations",
        str(ITERATIONS),
        "--horizon",
        str(HORIZON),
        "--hidden-size",
        str(HIDDEN_SIZE),
        "--transaction-cost-bps",
        str(PRIMARY_TRANSACTION_COST_BPS),
        "--borrow-fee-bps",
        str(PRIMARY_BORROW_FEE_BPS),
    ]
    run(common + ["--lambda-corr", str(PRIMARY_LAMBDA_CORR), "--output", str(primary)])
    run(common + ["--lambda-corr", str(ABLATION_LAMBDA_CORR), "--output", str(ablation)])
    return primary.with_suffix(".weights.npz"), ablation.with_suffix(".weights.npz")


def cpu_audit(output_dir: Path, dataset_path: Path, weights: Path, name: str) -> Path:
    audit = output_dir / f"{name}.audit.json"
    run(
        [
            sys.executable,
            "scripts/alphazerobeta_evaluate.py",
            "--dataset",
            str(dataset_path),
            "--weights",
            str(weights),
            "--output",
            str(audit),
            "--transaction-cost-bps",
            str(PRIMARY_TRANSACTION_COST_BPS),
            "--borrow-fee-bps",
            str(PRIMARY_BORROW_FEE_BPS),
        ]
    )
    return audit


def compare(
    output_dir: Path,
    dataset_path: Path,
    primary_weights: list[Path],
    ablation_weights: list[Path],
    *,
    transaction_cost_bps: float,
    borrow_fee_bps: float,
    name: str,
) -> Path:
    output = output_dir / name
    run(
        [
            sys.executable,
            "scripts/alphazerobeta_compare.py",
            "--dataset",
            str(dataset_path),
            "--primary-weights",
            *map(str, primary_weights),
            "--ablation-weights",
            *map(str, ablation_weights),
            "--output",
            str(output),
            "--transaction-cost-bps",
            str(transaction_cost_bps),
            "--borrow-fee-bps",
            str(borrow_fee_bps),
        ]
    )
    return output


def money(cumulative_return: float, initial: float) -> dict[str, float]:
    return {
        "initial_jpy": initial,
        "final_equity_jpy": initial * (1.0 + cumulative_return),
        "profit_loss_jpy": initial * cumulative_return,
    }


def write_summary(
    output_dir: Path,
    dataset_manifest: Path,
    source_manifest: Path,
    primary_folds: list[Path],
    ablation_folds: list[Path],
    primary_audits: list[Path],
    ablation_audits: list[Path],
    comparison: Path,
    sensitivity: list[Path],
) -> None:
    comparison_payload = read_json(comparison)
    primary = comparison_payload["primary_lambda_corr_0_5"]
    ablation = comparison_payload["ablation_lambda_corr_0"]
    assert isinstance(primary, dict) and isinstance(ablation, dict)
    primary_return = float(primary["cumulative_return"])
    ablation_return = float(ablation["cumulative_return"])
    primary_money_scaling = [money(primary_return, 1_000_000.0), money(primary_return, 10_000_000.0)]
    ablation_money_scaling = [money(ablation_return, 1_000_000.0), money(ablation_return, 10_000_000.0)]
    summary = {
        "schema_version": "investor2.alphazerobeta-empirical-summary.v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "validation_scope": "bounded fixed-universe independent mechanism validation",
        "result_is_live_trading_promise": False,
        "dataset_manifest": str(dataset_manifest),
        "dataset_manifest_sha256": sha256_file(dataset_manifest),
        "source_manifest": str(source_manifest),
        "source_manifest_sha256": sha256_file(source_manifest),
        "fold_count": int(comparison_payload["fold_count"]),
        "primary_lambda_corr_0_5": primary,
        "ablation_lambda_corr_0": ablation,
        "primary_money_scaling": primary_money_scaling,
        "ablation_money_scaling": ablation_money_scaling,
        "verdict": comparison_payload["verdict"],
        "gates": comparison_payload["gates"],
        "primary_fold_results": [str(path) for path in primary_folds],
        "ablation_fold_results": [str(path) for path in ablation_folds],
        "primary_cpu_audits": [str(path) for path in primary_audits],
        "ablation_cpu_audits": [str(path) for path in ablation_audits],
        "cost_sensitivity": [str(path) for path in sensitivity],
        "compute_contract": {
            "device": "cpu",
            "seed": SEED,
            "iterations_per_fold": ITERATIONS,
            "horizon": HORIZON,
            "hidden_size": HIDDEN_SIZE,
            "ppo_epochs": 10,
            "note": "Bounded compute for independent mechanism validation; not exact paper-scale reproduction.",
        },
    }
    summary_path = output_dir / "summary.json"
    write_json(summary_path, summary)

    p_money = primary_money_scaling
    a_money = ablation_money_scaling
    markdown = f"""# AlphaZeroBeta empirical validation — 2024 OOS\n\n- Verdict: **{summary["verdict"]}**\n- Fold count: {summary["fold_count"]}\n- Scope: bounded fixed-universe independent mechanism validation; not exact paper reproduction and not a live-trading promise.\n- Primary costs: {PRIMARY_TRANSACTION_COST_BPS:g} bps per side + {PRIMARY_BORROW_FEE_BPS:g} bps/year borrow.\n- Timing: features/decision at `t` are evaluated only against realized return at `t+1`.\n\n## Primary `lambda_corr=0.5`\n\n- Cumulative after-cost return: {100 * primary_return:.4f}%\n- Annualized Sharpe: {float(primary["annualized_sharpe"]):.4f}\n- Benchmark correlation: {float(primary["benchmark_correlation"]):.4f}\n- Maximum drawdown: {100 * float(primary["max_drawdown"]):.4f}%\n- JPY 1,000,000 -> JPY {float(p_money[0]["final_equity_jpy"]):,.0f} (P/L JPY {float(p_money[0]["profit_loss_jpy"]):+,.0f})\n- JPY 10,000,000 -> JPY {float(p_money[1]["final_equity_jpy"]):,.0f} (P/L JPY {float(p_money[1]["profit_loss_jpy"]):+,.0f})\n\n## Ablation `lambda_corr=0`\n\n- Cumulative after-cost return: {100 * ablation_return:.4f}%\n- Annualized Sharpe: {float(ablation["annualized_sharpe"]):.4f}\n- Benchmark correlation: {float(ablation["benchmark_correlation"]):.4f}\n- Maximum drawdown: {100 * float(ablation["max_drawdown"]):.4f}%\n- JPY 1,000,000 -> JPY {float(a_money[0]["final_equity_jpy"]):,.0f} (P/L JPY {float(a_money[0]["profit_loss_jpy"]):+,.0f})\n- JPY 10,000,000 -> JPY {float(a_money[1]["final_equity_jpy"]):,.0f} (P/L JPY {float(a_money[1]["profit_loss_jpy"]):+,.0f})\n\n## Gates\n\n```json\n{json.dumps(summary["gates"], ensure_ascii=False, indent=2, sort_keys=True)}\n```\n"""
    (output_dir / "SUMMARY.md").write_text(markdown, encoding="utf-8")


def execute(output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        output_dir / "run_contract.json",
        {
            "schema_version": "investor2.alphazerobeta-empirical-run-contract.v1",
            "market_data_provider": MARKET_DATA_PROVIDER,
            "candidate_etfs": list(CANDIDATE_ETFS),
            "benchmark": BENCHMARK,
            "source_start": SOURCE_START,
            "source_end": SOURCE_END,
            "universe_cutoff": UNIVERSE_CUTOFF,
            "test_start": TEST_START,
            "test_end": TEST_END,
            "max_assets": MAX_ASSETS,
            "seed": SEED,
            "iterations": ITERATIONS,
            "horizon": HORIZON,
            "hidden_size": HIDDEN_SIZE,
            "primary_lambda_corr": PRIMARY_LAMBDA_CORR,
            "ablation_lambda_corr": ABLATION_LAMBDA_CORR,
            "primary_transaction_cost_bps_per_side": PRIMARY_TRANSACTION_COST_BPS,
            "primary_borrow_fee_bps_per_year": PRIMARY_BORROW_FEE_BPS,
        },
    )
    prices_path, benchmark_path, source_manifest = build_market_inputs(output_dir)
    dataset_path = output_dir / "etf_panel.npz"
    dataset_manifest = output_dir / "etf_panel.npz.manifest.json"
    run(
        [
            sys.executable,
            "scripts/alphazerobeta_prepare.py",
            "--prices-csv",
            str(prices_path),
            "--benchmark-csv",
            str(benchmark_path),
            "--output",
            str(dataset_path),
            "--manifest",
            str(dataset_manifest),
            "--max-assets",
            str(MAX_ASSETS),
            "--universe-cutoff",
            UNIVERSE_CUTOFF,
        ]
    )

    primary_weights: list[Path] = []
    ablation_weights: list[Path] = []
    primary_results: list[Path] = []
    ablation_results: list[Path] = []
    primary_audits: list[Path] = []
    ablation_audits: list[Path] = []
    for fold_index in (0, 1):
        primary_weight, ablation_weight = train_pair(output_dir, dataset_path, fold_index)
        primary_weights.append(primary_weight)
        ablation_weights.append(ablation_weight)
        primary_result = output_dir / f"primary_fold{fold_index}.json"
        ablation_result = output_dir / f"ablation_fold{fold_index}.json"
        primary_results.append(primary_result)
        ablation_results.append(ablation_result)
        primary_audits.append(cpu_audit(output_dir, dataset_path, primary_weight, f"primary_fold{fold_index}"))
        ablation_audits.append(cpu_audit(output_dir, dataset_path, ablation_weight, f"ablation_fold{fold_index}"))

    comparison = compare(
        output_dir,
        dataset_path,
        primary_weights,
        ablation_weights,
        transaction_cost_bps=PRIMARY_TRANSACTION_COST_BPS,
        borrow_fee_bps=PRIMARY_BORROW_FEE_BPS,
        name="alphazerobeta_comparison.json",
    )
    sensitivity: list[Path] = []
    for trading_bps in (5.0, 15.0, 30.0):
        for borrow_bps in (0.0, 100.0):
            name = f"comparison_cost_{int(trading_bps)}bps_borrow_{int(borrow_bps)}bps.json"
            sensitivity.append(
                compare(
                    output_dir,
                    dataset_path,
                    primary_weights,
                    ablation_weights,
                    transaction_cost_bps=trading_bps,
                    borrow_fee_bps=borrow_bps,
                    name=name,
                )
            )
    write_summary(
        output_dir,
        dataset_manifest,
        source_manifest,
        primary_results,
        ablation_results,
        primary_audits,
        ablation_audits,
        comparison,
        sensitivity,
    )


def main() -> None:
    args = parse_args()
    try:
        execute(args.output_dir)
    except Exception as exc:  # noqa: BLE001 - failure evidence must persist
        args.output_dir.mkdir(parents=True, exist_ok=True)
        write_json(
            args.output_dir / "run_failure.json",
            {
                "schema_version": "investor2.alphazerobeta-empirical-failure.v1",
                "failed_at": datetime.now(UTC).isoformat(),
                "exception_type": type(exc).__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(),
            },
        )
        raise


if __name__ == "__main__":
    main()