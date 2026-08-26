#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd

from src.research.alpha_discovery_priority1 import run_ablation


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Issue #222 Priority-1 alpha-discovery matched ablation.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--dataset-manifest", required=True, type=Path)
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--plot", required=True, type=Path)
    return parser.parse_args()


def _bounds(dates: pd.DatetimeIndex, start: str, end_exclusive: str) -> tuple[int, int]:
    left = int(dates.searchsorted(pd.Timestamp(start), side="left"))
    right = int(dates.searchsorted(pd.Timestamp(end_exclusive), side="left"))
    if right <= left:
        raise AssertionError(f"empty interval {start}..{end_exclusive}")
    return left, right


def _git_revision() -> str:
    env_sha = os.environ.get("GITHUB_SHA")
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return env_sha or "UNKNOWN"


def _effective_range(dates: pd.DatetimeIndex, bounds: tuple[int, int]) -> dict[str, str]:
    start, end = bounds
    return {"start": str(dates[start].date()), "end": str(dates[end - 1].date())}


def write_plot(path: Path, result: dict[str, object]) -> None:
    arm_results = dict(dict(result["ablation"])["arms"])
    labels = [
        ("baseline", "Baseline"),
        ("ast_originality", "AST originality"),
        ("semantic_schema", "Semantic schema"),
    ]
    survivors = [int(dict(arm_results[key])["unique_oos_survivors"]) for key, _ in labels]
    structural = [int(dict(arm_results[key])["unique_structural_candidates_evaluated"]) for key, _ in labels]
    semantic = [int(dict(arm_results[key])["unique_semantic_schemas_evaluated"]) for key, _ in labels]
    best_sharpe = [float(dict(arm_results[key])["best_finalist_oos_sharpe"]) for key, _ in labels]
    maximum = max(max(survivors), 1)
    width = 1200
    height = 720
    base_y = 500
    bar_max = 300
    x_positions = [210, 540, 870]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="1200" height="720" fill="#ffffff"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;fill:#111827}.title{font-size:30px;font-weight:700}.sub{font-size:16px;fill:#4b5563}.label{font-size:17px;font-weight:600}.metric{font-size:14px;fill:#374151}.value{font-size:22px;font-weight:700}.axis{stroke:#9ca3af;stroke-width:1}.bar{fill:#4b5563}</style>',
        '<text x="60" y="58" class="title">Priority 1: originality / semantic control</text>',
        '<text x="60" y="88" class="sub">Primary: unique untouched-OOS survivors per 24 validation evaluator calls</text>',
        f'<line x1="100" y1="{base_y}" x2="1100" y2="{base_y}" class="axis"/>',
    ]
    for index, ((key, label), x) in enumerate(zip(labels, x_positions, strict=True)):
        value = survivors[index]
        bar_height = bar_max * value / maximum
        y = base_y - bar_height
        parts.extend(
            [
                f'<rect x="{x}" y="{y:.1f}" width="160" height="{bar_height:.1f}" class="bar"/>',
                f'<text x="{x + 80}" y="{max(y - 12, 125):.1f}" text-anchor="middle" class="value">{value}</text>',
                f'<text x="{x + 80}" y="{base_y + 35}" text-anchor="middle" class="label">{escape(label)}</text>',
                f'<text x="{x + 80}" y="{base_y + 62}" text-anchor="middle" class="metric">structural unique: {structural[index]}/24</text>',
                f'<text x="{x + 80}" y="{base_y + 84}" text-anchor="middle" class="metric">semantic unique: {semantic[index]}/24</text>',
                f'<text x="{x + 80}" y="{base_y + 106}" text-anchor="middle" class="metric">best OOS Sharpe: {best_sharpe[index]:.3f}</text>',
            ]
        )
    winners = ", ".join(str(value) for value in dict(result["ablation"])["winner_by_primary"])
    parts.extend(
        [
            f'<text x="60" y="665" class="sub">Winner(s) by frozen primary metric: {escape(winners)}</text>',
            '<text x="60" y="693" class="sub">Mechanism evidence only; no paper-family BEAT/TIE/LOSE verdict is implied.</text>',
            '</svg>',
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    manifest = json.loads(args.dataset_manifest.read_text(encoding="utf-8"))
    with np.load(args.dataset, allow_pickle=False) as data:
        dates_raw = data["dates"].astype(str)
        feature_names = data["feature_names"].astype(str).tolist()
        features = data["features"].astype(np.float64)
        returns = data["returns"].astype(np.float64)
        benchmark = data["benchmark"].astype(np.float64)

    if features.shape[:2] != returns.shape:
        raise AssertionError("features and returns do not align")
    if features.shape[2] != len(feature_names):
        raise AssertionError("feature names do not match feature tensor")
    expected_assets = int(dict(contract["dataset"])["max_assets"])
    if features.shape[1] != expected_assets:
        raise AssertionError(f"expected {expected_assets} assets, got {features.shape[1]}")
    expected_cutoff = str(dict(contract["dataset"])["universe_cutoff"])
    if str(manifest.get("universe_cutoff")) != expected_cutoff:
        raise AssertionError(f"universe cutoff drifted: {manifest.get('universe_cutoff')} != {expected_cutoff}")

    dates = pd.DatetimeIndex(pd.to_datetime(dates_raw.tolist()))
    split = dict(contract["split"])
    train = _bounds(dates, str(split["train_calendar_start"]), str(split["validation_calendar_start"]))
    validation = _bounds(
        dates,
        str(split["validation_calendar_start"]),
        str(split["untouched_oos_calendar_start"]),
    )
    oos_end_exclusive = str((pd.Timestamp(str(split["untouched_oos_calendar_end"])) + pd.Timedelta(days=1)).date())
    oos = _bounds(dates, str(split["untouched_oos_calendar_start"]), oos_end_exclusive)

    budget = dict(contract["budget"])
    portfolio = dict(contract["portfolio"])
    ablation = run_ablation(
        feature_names=feature_names,
        feature_tensor=features,
        returns=returns,
        benchmark=benchmark,
        train=train,
        validation=validation,
        oos=oos,
        evaluator_budget=int(budget["validation_evaluator_calls_per_arm"]),
        finalists=int(budget["oos_finalists_per_arm"]),
        n_long=int(portfolio["n_long"]),
        n_short=int(portfolio["n_short"]),
        beta=float(portfolio["beta"]),
        gamma=float(portfolio["gamma"]),
        transaction_cost_bps=float(portfolio["transaction_cost_bps_per_side"]),
        borrow_fee_bps=float(portfolio["borrow_fee_bps_per_year"]),
    )

    result = {
        "schema_version": "investor2.alpha-discovery-priority1-result.v1",
        "research_date": "2026-08-26",
        "execution_status": "COMPLETED",
        "issues": [194, 222],
        "claim_boundary": contract["claim_boundary"],
        "contract": {
            "path": str(args.contract),
            "sha256": sha256_file(args.contract),
        },
        "code_revision": _git_revision(),
        "dataset": {
            "path": str(args.dataset),
            "sha256": sha256_file(args.dataset),
            "manifest_path": str(args.dataset_manifest),
            "manifest_sha256": sha256_file(args.dataset_manifest),
            "assets": int(features.shape[1]),
            "features": int(features.shape[2]),
            "trading_days": int(features.shape[0]),
            "universe_cutoff": manifest.get("universe_cutoff"),
            "date_start": str(dates[0].date()),
            "date_end": str(dates[-1].date()),
        },
        "effective_split": {
            "train": _effective_range(dates, train),
            "validation": _effective_range(dates, validation),
            "untouched_oos": _effective_range(dates, oos),
        },
        "frozen_primary_metric": contract["primary_metric"],
        "survivor_gate": contract["survivor_gate"],
        "ablation": ablation,
        "frontier_verdict": None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_plot(args.plot, result)
    summary = {
        arm: {
            "unique_oos_survivors": int(dict(payload)["unique_oos_survivors"]),
            "unique_structural_candidates_evaluated": int(dict(payload)["unique_structural_candidates_evaluated"]),
            "unique_semantic_schemas_evaluated": int(dict(payload)["unique_semantic_schemas_evaluated"]),
            "best_finalist_oos_sharpe": float(dict(payload)["best_finalist_oos_sharpe"]),
        }
        for arm, payload in dict(ablation["arms"]).items()
    }
    print(json.dumps({"winner_by_primary": ablation["winner_by_primary"], "arms": summary}, sort_keys=True))


if __name__ == "__main__":
    main()
