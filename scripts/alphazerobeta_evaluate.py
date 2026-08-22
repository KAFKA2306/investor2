#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.research.alphazerobeta import evaluate_weight_path, metrics_to_dict, write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CPU-side audit of an AlphaZeroBeta GPU weight artifact.")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--weights", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--transaction-cost-bps", type=float, default=15.0)
    parser.add_argument("--borrow-fee-bps", type=float, default=100.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset = np.load(args.dataset, allow_pickle=False)
    artifact = np.load(args.weights, allow_pickle=False)
    dates = dataset["dates"].astype(str)
    weight_dates = artifact["dates"].astype(str)
    lookup = {date: i for i, date in enumerate(dates)}
    missing = [date for date in weight_dates if date not in lookup]
    if missing:
        raise AssertionError(f"weight dates missing from dataset: {missing[:3]}")
    indices = np.asarray([lookup[date] for date in weight_dates], dtype=np.int64)
    weights = artifact["weights"].astype(np.float32)
    asset_returns = dataset["returns"][indices].astype(np.float32)
    benchmark = dataset["benchmark"][indices].astype(np.float32)
    metrics, _ = evaluate_weight_path(
        weights,
        asset_returns,
        benchmark,
        transaction_cost_bps_per_side=args.transaction_cost_bps,
        borrow_fee_bps_per_year=args.borrow_fee_bps,
    )
    write_json(
        args.output,
        {
            "schema_version": "investor2.alphazerobeta-cpu-audit.v1",
            "weights_artifact": str(args.weights),
            "dataset": str(args.dataset),
            "cost_assumptions": {
                "transaction_cost_bps_per_side": args.transaction_cost_bps,
                "borrow_fee_bps_per_year": args.borrow_fee_bps,
            },
            "metrics": metrics_to_dict(metrics),
        },
    )
    print(json.dumps({"audit": str(args.output), "metrics": metrics_to_dict(metrics)}))


if __name__ == "__main__":
    main()
