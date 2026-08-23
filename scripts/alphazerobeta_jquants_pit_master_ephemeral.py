#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pandas as pd

from scripts.alphazerobeta_jquants_free_ephemeral import (
    MIN_REQUEST_INTERVAL_SECONDS,
    make_rate_limited_client,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch one point-in-time J-Quants issue master ephemerally.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--request-interval", type=float, default=MIN_REQUEST_INTERVAL_SECONDS)
    return parser.parse_args()


def normalize_master(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Code", "Mkt"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise AssertionError(f"J-Quants PIT master missing columns: {missing}")
    out = frame.copy()
    out["Code"] = out["Code"].astype(str)
    out["Ticker"] = out["Code"]
    out["Region"] = "jp"
    if "Date" in out.columns:
        out["Date"] = pd.to_datetime(out["Date"], errors="raise").dt.tz_localize(None)
    if out["Code"].duplicated().any():
        raise AssertionError("duplicate Code rows in J-Quants PIT master")
    return out.sort_values("Code").reset_index(drop=True)


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required")
    if args.request_interval < MIN_REQUEST_INTERVAL_SECONDS:
        raise ValueError(f"request interval must be >= {MIN_REQUEST_INTERVAL_SECONDS}s")

    requested = pd.Timestamp(args.date).normalize()
    client = make_rate_limited_client(api_key, args.request_interval)
    master = normalize_master(client.get_eq_master(date=requested.strftime("%Y%m%d")))
    if master.empty:
        raise AssertionError(f"J-Quants PIT master is empty for {requested.date()}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    master.to_parquet(args.output, index=False, compression="zstd")
    print(
        json.dumps(
            {
                "requested_date": str(requested.date()),
                "rows": int(len(master)),
                "http_requests": int(client.request_count),
                "retention": "ephemeral local file only",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
