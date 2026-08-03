from pathlib import Path

import pandas as pd

from src.io.frozen_split import (
    DEFAULT_MANIFEST_PATH,
    DEFAULT_SOURCE_PATH,
    build_frozen_split,
    load_frozen_split_manifest,
    validate_source_file,
)

# EDINET-Bench Data Loader
# Utility module to load datasets for EDINET-Bench tasks.

BASE_PATH = Path("cache/benchmarks/edinet-bench")


def _load_parquet(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return pd.read_parquet(path)


def load_fraud_detection(split: str = "train") -> pd.DataFrame:
    """Load a Fraud Detection dataset split."""
    return _load_parquet(BASE_PATH / "fraud_detection" / f"{split}-00000-of-00001.parquet")


def load_earnings_forecast(split: str = "train") -> pd.DataFrame:
    """Load an Earnings Forecast dataset split."""
    return _load_parquet(BASE_PATH / "earnings_forecast" / f"{split}-00000-of-00001.parquet")


def load_industry_prediction(split: str = "train") -> pd.DataFrame:
    """Load the source Industry Prediction split.

    EDINET-Bench currently publishes only a train split for this task. Formal
    evaluation must use ``load_industry_prediction_frozen`` instead.
    """
    return _load_parquet(BASE_PATH / "industry_prediction" / f"{split}-00000-of-00001.parquet")


def load_industry_prediction_frozen(
    split: str = "frozen_evaluation",
    *,
    source_path: Path = DEFAULT_SOURCE_PATH,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Load a deterministic development or frozen evaluation partition.

    The source parquet revision and SHA256 are pinned by the committed manifest.
    Any upstream dataset change fails closed instead of silently redefining the
    benchmark population.
    """
    if split not in {"development", "frozen_evaluation"}:
        raise ValueError(f"Unknown industry split: {split}")
    manifest = load_frozen_split_manifest(manifest_path)
    source_sha256 = validate_source_file(source_path, manifest)
    source = _load_parquet(source_path)
    development, evaluation, evidence = build_frozen_split(source, manifest)
    evidence = {**evidence, "validated_source_sha256": source_sha256}
    return (development if split == "development" else evaluation), evidence


if __name__ == "__main__":
    print("EDINET-Bench Data Loading Test")
    print(f"Fraud Detection (train): {len(load_fraud_detection())} rows")
    print(f"Earnings Forecast (train): {len(load_earnings_forecast())} rows")
    industry, evidence = load_industry_prediction_frozen()
    print(f"Industry Prediction (frozen evaluation): {len(industry)} rows")
    print(f"Frozen split manifest: {evidence['manifest_sha256']}")
    print("All datasets loaded successfully.")
