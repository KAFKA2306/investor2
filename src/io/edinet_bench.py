import pandas as pd
from pathlib import Path

# EDINET-Bench Data Loader 🎀
# このファイルは EDINET-Bench の各タスクのデータを読み込むためのユーティリティだよっ！ ✨

BASE_PATH = Path("cache/benchmarks/edinet-bench")

def load_fraud_detection(split="train"):
    """
    不正検知 (Fraud Detection) のデータを読み込むよっ！ ⚖️
    """
    path = BASE_PATH / "fraud_detection" / f"{split}-00000-of-00001.parquet"
    if not path.exists():
        raise FileNotFoundError(f"データが見つからないよぉ…💦: {path}")
    return pd.read_parquet(path)

def load_earnings_forecast(split="train"):
    """
    業績予想 (Earnings Forecast) のデータを読み込むよっ！ 📈
    """
    path = BASE_PATH / "earnings_forecast" / f"{split}-00000-of-00001.parquet"
    if not path.exists():
        raise FileNotFoundError(f"データが見つからないよぉ…💦: {path}")
    return pd.read_parquet(path)

def load_industry_prediction(split="train"):
    """
    業種判定 (Industry Prediction) のデータを読み込むよっ！ 🏢
    ※ このタスクは train のみ存在するよっ！
    """
    path = BASE_PATH / "industry_prediction" / f"{split}-00000-of-00001.parquet"
    if not path.exists():
        raise FileNotFoundError(f"データが見つからないよぉ…💦: {path}")
    return pd.read_parquet(path)

if __name__ == "__main__":
    # 動作確認だよっ！ ✨
    print("✨ EDINET-Bench Data Loading Test ✨")
    print(f"Fraud Detection (train): {len(load_fraud_detection())} rows")
    print(f"Earnings Forecast (train): {len(load_earnings_forecast())} rows")
    print(f"Industry Prediction (train): {len(load_industry_prediction())} rows")
    print("All datasets loaded successfully! 💖🌈")
