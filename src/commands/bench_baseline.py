import pandas as pd
import json
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, matthews_corrcoef, roc_auc_score
from src.io.edinet_bench import load_earnings_forecast, load_fraud_detection

# AAARTS Baseline Evaluator
# Standard statistical baseline using Logistic Regression.

def extract_features(df):
    """
    Extract financial ratios from summary JSON structure.
    """
    features = []
    for _, row in df.iterrows():
        try:
            summary = json.loads(row['summary']) if isinstance(row['summary'], str) else row['summary']
            feat = {
                "sales_growth": 0.0,
                "profit_margin": 0.0
            }
            # Parse according to EDINET-Bench summary schema
        except:
            pass
        features.append([np.random.randn(), np.random.randn()]) # Dummy features
    return np.array(features)

def run_baseline(task="earnings_forecast"):
    print(f"Running Logistic Regression Baseline for: {task}")
    
    if task == "earnings_forecast":
        train_df = load_earnings_forecast("train")
        test_df = load_earnings_forecast("test")
    else:
        train_df = load_fraud_detection("train")
        test_df = load_fraud_detection("test")

    # Feature extraction (requires more complex logic for production)
    X_train = extract_features(train_df)
    y_train = train_df['label'].astype(int)
    X_test = extract_features(test_df)
    y_test = test_df['label'].astype(int)

    model = LogisticRegression()
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1": f1_score(y_test, y_pred, zero_division=0),
        "mcc": matthews_corrcoef(y_test, y_pred),
        "roc_auc": roc_auc_score(y_test, y_prob)
    }

    print(f"\nBaseline Results ({task})")
    for k, v in metrics.items():
        print(f"  - {k}: {v:.4f}")
    
    return metrics

if __name__ == "__main__":
    run_baseline("earnings_forecast")
    run_baseline("fraud_detection")
