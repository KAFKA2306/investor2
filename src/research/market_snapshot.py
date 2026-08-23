from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class MarketSnapshot:
    root: Path

    def path(self, relative: str) -> Path:
        candidate = (self.root / relative).resolve()
        root = self.root.resolve()
        if candidate != root and root not in candidate.parents:
            raise AssertionError(f"snapshot path escapes root: {relative}")
        return candidate


def load_manifest(snapshot: MarketSnapshot) -> dict[str, object]:
    path = snapshot.path("manifest.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AssertionError("market snapshot manifest must be a JSON object")
    return {str(key): value for key, value in payload.items()}


def load_universe(snapshot: MarketSnapshot) -> pd.DataFrame:
    return pd.read_parquet(snapshot.path("universe.parquet"))


def load_benchmark(snapshot: MarketSnapshot) -> pd.DataFrame:
    return pd.read_parquet(snapshot.path("benchmark.parquet"))


def load_prices(snapshot: MarketSnapshot, *, regions: list[str] | None = None) -> pd.DataFrame:
    selected = [region.lower() for region in regions] if regions else ["*"]
    files = sorted(
        {path for region in selected for path in snapshot.path("prices").glob(f"{region}/*.parquet") if path.is_file()}
    )
    if not files:
        raise FileNotFoundError(f"no materialized price partitions under {snapshot.root}: {selected}")
    return pd.concat((pd.read_parquet(path) for path in files), ignore_index=True)
