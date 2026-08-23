#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from io import BytesIO
from pathlib import Path

import pandas as pd

from scripts.alphazerobeta_jquants_free_collect import (
    decrypt_blob,
    derive_cache_key,
    encrypt_blob,
    make_rate_limited_client,
    normalize_master,
    parquet_bytes,
)

REQUEST_INTERVAL_SECONDS = 15.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize a point-in-time J-Quants issue master and cache it encrypted on Hugging Face."
    )
    parser.add_argument("--date", required=True)
    parser.add_argument("--hf-repo-id", required=True)
    parser.add_argument("--snapshot-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if not api_key:
        raise RuntimeError("JQUANTS_API_KEY is required")
    if not hf_token:
        raise RuntimeError("HF_TOKEN is required")

    requested = pd.Timestamp(args.date).normalize()
    date_text = requested.strftime("%Y%m%d")
    raw_path = f"staging/{args.snapshot_id}/masters/{requested.date()}.parquet"
    encrypted_path = f"{raw_path}.enc"
    cache_key = derive_cache_key(api_key)

    from huggingface_hub import HfApi, hf_hub_download

    api = HfApi(token=hf_token)
    files = set(api.list_repo_files(repo_id=args.hf_repo_id, repo_type="dataset"))
    resumed = encrypted_path in files
    if resumed:
        cached = hf_hub_download(
            repo_id=args.hf_repo_id,
            repo_type="dataset",
            filename=encrypted_path,
            token=hf_token,
        )
        plaintext = decrypt_blob(
            Path(cached).read_bytes(),
            key=cache_key,
            aad=raw_path.encode("utf-8"),
        )
        master = pd.read_parquet(BytesIO(plaintext))
    else:
        client = make_rate_limited_client(api_key, REQUEST_INTERVAL_SECONDS)
        master = normalize_master(client.get_eq_master(date=date_text))
        if master.empty:
            raise AssertionError(f"J-Quants issue master is empty for {requested.date()}")
        ciphertext = encrypt_blob(
            parquet_bytes(master),
            key=cache_key,
            aad=raw_path.encode("utf-8"),
        )
        api.upload_file(
            repo_id=args.hf_repo_id,
            repo_type="dataset",
            path_or_fileobj=ciphertext,
            path_in_repo=encrypted_path,
            commit_message=f"cache encrypted PIT J-Quants master {requested.date()}",
        )

    if "Mkt" not in master.columns:
        raise AssertionError("J-Quants PIT master is missing Mkt")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    master.to_parquet(args.output, index=False, compression="zstd")
    print(
        json.dumps(
            {
                "requested_date": str(requested.date()),
                "rows": int(len(master)),
                "resumed_from_hf": resumed,
                "hf_path": encrypted_path,
                "plaintext_raw_data_on_hf": False,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
