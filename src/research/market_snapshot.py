from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download, snapshot_download


@dataclass(frozen=True)
class MarketSnapshot:
    repo_id: str
    revision: str = "main"


def _snapshot_root(snapshot: MarketSnapshot, patterns: list[str]) -> Path:
    return Path(
        snapshot_download(
            repo_id=snapshot.repo_id,
            repo_type="dataset",
            revision=snapshot.revision,
            allow_patterns=patterns,
        )
    )


def load_manifest(snapshot: MarketSnapshot) -> dict[str, object]:
    path = Path(
        hf_hub_download(
            repo_id=snapshot.repo_id,
            repo_type="dataset",
            revision=snapshot.revision,
            filename="manifest.json",
        )
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("market snapshot manifest must be a JSON object")
    return {str(key): value for key, value in payload.items()}


def load_universe(snapshot: MarketSnapshot) -> pd.DataFrame:
    path = hf_hub_download(
        repo_id=snapshot.repo_id,
        repo_type="dataset",
        revision=snapshot.revision,
        filename="universe.parquet",
    )
    return pd.read_parquet(path)


def load_benchmark(snapshot: MarketSnapshot) -> pd.DataFrame:
    path = hf_hub_download(
        repo_id=snapshot.repo_id,
        repo_type="dataset",
        revision=snapshot.revision,
        filename="benchmark.parquet",
    )
    return pd.read_parquet(path)


def load_prices(snapshot: MarketSnapshot, *, regions: list[str] | None = None) -> pd.DataFrame:
    selected = [region.lower() for region in regions] if regions else ["*"]
    patterns = [f"prices/{region}/*.parquet" for region in selected]
    root = _snapshot_root(snapshot, patterns)
    files = sorted({path for pattern in patterns for path in root.glob(pattern)})
    if not files:
        raise FileNotFoundError(f"no cached price partitions for {snapshot.repo_id}@{snapshot.revision}: {selected}")
    return pd.concat((pd.read_parquet(path) for path in files), ignore_index=True)
