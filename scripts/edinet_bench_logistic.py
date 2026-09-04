#!/usr/bin/env python3
"""Reproduce the official EDINET-Bench summary-only logistic baselines."""

from __future__ import annotations

import argparse
import importlib
import json
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

DATASET_ID = "SakanaAI/EDINET-Bench"
DATASET_REVISION = "cf0bc74fb85cce99878f15426f8cf3ba750d0cba"
UPSTREAM_REPOSITORY = "https://github.com/SakanaAI/EDINET-Bench"
UPSTREAM_COMMIT = "797fbb50051c14b97ee2fd88595b0a3c12432058"
UPSTREAM_LOGISTIC_BLOB = "37184505cd88d4bacdfa8576778da59dd32e434c"
DATA_KEY = "summary"
TASKS = ("fraud_detection", "earnings_forecast")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reproduce EDINET-Bench fraud/earnings summary-only logistic baselines."
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def preprocess_data(data_list: list[dict[str, Any]]) -> pd.DataFrame:
    """Mirror SakanaAI/EDINET-Bench logistic.py summary flattening."""
    rows: list[dict[str, float | int]] = []
    for data in data_list:
        row: dict[str, float | int] = {}
        for key, values in data.items():
            if key == "label":
                row[key] = int(values)
            elif values is not None:
                if not isinstance(values, dict):
                    raise TypeError(f"expected mapping for summary field {key}, got {type(values).__name__}")
                for year, value in values.items():
                    column = f"{key}_{year}"
                    row[column] = float(value) if value not in ["－", None] else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def fill_and_align_data(x_train: pd.DataFrame, x_test: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Mirror the official train-mean fill, constant-drop, and column alignment."""
    train = x_train.copy()
    test = x_test.copy()
    train_mean = train.mean(numeric_only=True)
    train.fillna(train_mean, inplace=True)
    test.fillna(train_mean, inplace=True)

    constant_columns = train.columns[train.nunique() <= 1]
    train.drop(columns=constant_columns, inplace=True)
    test.drop(columns=constant_columns, inplace=True, errors="ignore")
    test = test.reindex(columns=train.columns)
    return train, test


def load_frame(task: str, split: str) -> tuple[pd.DataFrame, list[str]]:
    datasets_module: Any = importlib.import_module("datasets")
    dataset: Any = datasets_module.load_dataset(
        DATASET_ID,
        task,
        revision=DATASET_REVISION,
        split=split,
    )
    doc_ids = [str(doc_id) for doc_id in dataset["doc_id"]]
    records: list[dict[str, Any]] = []
    for example in dataset:
        summary = json.loads(str(example[DATA_KEY]))
        if not isinstance(summary, dict):
            raise TypeError(f"{task}/{split} summary is not a JSON object")
        records.append({**summary, "label": int(example["label"])})
    return preprocess_data(records), doc_ids


def binary_metrics(y_true: np.ndarray, y_pred: np.ndarray, y_probability: np.ndarray) -> dict[str, object]:
    metrics_module: Any = importlib.import_module("sklearn.metrics")
    return {
        "accuracy": float(metrics_module.accuracy_score(y_true, y_pred)),
        "precision": float(metrics_module.precision_score(y_true, y_pred)),
        "recall": float(metrics_module.recall_score(y_true, y_pred)),
        "f1": float(metrics_module.f1_score(y_true, y_pred)),
        "roc_auc": float(metrics_module.roc_auc_score(y_true, y_probability)),
        "confusion_matrix": metrics_module.confusion_matrix(y_true, y_pred).astype(int).tolist(),
    }


def evaluate_task(task: str) -> dict[str, object]:
    train, train_doc_ids = load_frame(task, "train")
    test, test_doc_ids = load_frame(task, "test")

    x_train = train.drop(columns=["label"])
    y_train = train["label"].to_numpy(dtype=np.int64)
    x_test = test.drop(columns=["label"])
    y_test = test["label"].to_numpy(dtype=np.int64)
    x_train, x_test = fill_and_align_data(x_train, x_test)

    preprocessing_module: Any = importlib.import_module("sklearn.preprocessing")
    linear_model_module: Any = importlib.import_module("sklearn.linear_model")
    scaler: Any = preprocessing_module.StandardScaler()
    scaled_train = scaler.fit_transform(x_train)
    scaled_test = scaler.transform(x_test)

    model: Any = linear_model_module.LogisticRegression()
    model.fit(scaled_train, y_train)
    y_pred = np.asarray(model.predict(scaled_test), dtype=np.int64)
    probabilities = np.asarray(model.predict_proba(scaled_test)[:, 1], dtype=np.float64)

    return {
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "train_doc_ids_unique": len(train_doc_ids) == len(set(train_doc_ids)),
        "test_doc_ids_unique": len(test_doc_ids) == len(set(test_doc_ids)),
        "feature_count_after_official_preprocessing": int(x_train.shape[1]),
        "train_positive": int(y_train.sum()),
        "test_positive": int(y_test.sum()),
        "metrics": binary_metrics(y_test, y_pred, probabilities),
    }


def package_versions() -> dict[str, str]:
    packages = ("datasets", "scikit-learn", "pandas", "numpy", "pyarrow")
    return {package: version(package) for package in packages}


def main() -> None:
    args = parse_args()
    tasks = {task: evaluate_task(task) for task in TASKS}
    payload: dict[str, object] = {
        "schema_version": "investor2.edinet-bench-logistic-reproduction.v1",
        "execution_status": "completed",
        "family": "EDINET-Bench",
        "reproduction_scope": "official summary-only logistic baseline",
        "claim_boundary": (
            "Reproduces the official deterministic logistic baselines for fraud_detection and "
            "earnings_forecast only. This is not an AAARTS candidate, not a head-to-head result, "
            "and does not justify BEAT/TIE/LOSE."
        ),
        "upstream": {
            "repository": UPSTREAM_REPOSITORY,
            "repository_commit": UPSTREAM_COMMIT,
            "official_logistic_blob": UPSTREAM_LOGISTIC_BLOB,
            "dataset_id": DATASET_ID,
            "dataset_revision": DATASET_REVISION,
            "data_key": DATA_KEY,
        },
        "algorithm_contract": {
            "summary_flattening": "metric/year -> numeric column; Japanese dash and null -> NaN",
            "missing_values": "train numeric mean applied to train and test",
            "constant_columns": "drop train columns with <=1 unique value; align test to train",
            "scaling": "sklearn StandardScaler",
            "model": "sklearn LogisticRegression with default constructor arguments",
            "tasks": list(TASKS),
        },
        "environment": package_versions(),
        "tasks": tasks,
        "frontier": {
            "reproduction_state": "BASELINE_REPRODUCED",
            "head_to_head": "NOT_RUN",
            "verdict": None,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
