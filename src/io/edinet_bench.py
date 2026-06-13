import pandas as pd
from pathlib import Path

# EDINET-Bench Data Loader
# Utility module to load datasets for EDINET-Bench tasks.

BASE_PATH = Path("cache/benchmarks/edinet-bench")

def load_fraud_detection(split="train"):
    """
    Load Fraud Detection dataset split.
    """
    path = BASE_PATH / "fraud_detection" / f"{split}-00000-of-00001.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return pd.read_parquet(path)

def load_earnings_forecast(split="train"):
    """
    Load Earnings Forecast dataset split.
    """
    path = BASE_PATH / "earnings_forecast" / f"{split}-00000-of-00001.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return pd.read_parquet(path)

def load_industry_prediction(split="train"):
    """
    Load Industry Prediction dataset split.
    Note: This task only contains a train split.
    """
    path = BASE_PATH / "industry_prediction" / f"{split}-00000-of-00001.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {path}")
    return pd.read_parquet(path)

if __name__ == "__main__":
    print("EDINET-Bench Data Loading Test")
    print(f"Fraud Detection (train): {len(load_fraud_detection())} rows")
    print(f"Earnings Forecast (train): {len(load_earnings_forecast())} rows")
    print(f"Industry Prediction (train): {len(load_industry_prediction())} rows")
    print("All datasets loaded successfully.")
