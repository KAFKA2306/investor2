from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np
import pandas as pd


def load_module() -> ModuleType:
    path = Path(__file__).resolve().parents[1] / "scripts" / "edinet_bench_logistic.py"
    spec = importlib.util.spec_from_file_location("edinet_bench_logistic", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load edinet_bench_logistic module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preprocess_data_matches_official_flattening() -> None:
    module = load_module()
    frame = module.preprocess_data(
        [
            {
                "revenue": {"2023": "100.5", "2024": "－"},
                "profit": {"2023": None, "2024": "12"},
                "label": 1,
            }
        ]
    )
    assert frame.loc[0, "revenue_2023"] == 100.5
    assert np.isnan(frame.loc[0, "revenue_2024"])
    assert np.isnan(frame.loc[0, "profit_2023"])
    assert frame.loc[0, "profit_2024"] == 12.0
    assert frame.loc[0, "label"] == 1


def test_fill_and_align_uses_train_mean_and_drops_constants() -> None:
    module = load_module()
    train = pd.DataFrame(
        {
            "varying": [1.0, np.nan, 3.0],
            "constant": [7.0, 7.0, 7.0],
            "train_only": [2.0, 4.0, 8.0],
        }
    )
    test = pd.DataFrame(
        {
            "varying": [np.nan, 5.0],
            "constant": [7.0, 7.0],
            "test_only": [9.0, 10.0],
        }
    )

    aligned_train, aligned_test = module.fill_and_align_data(train, test)

    assert list(aligned_train.columns) == ["varying", "train_only"]
    assert list(aligned_test.columns) == ["varying", "train_only"]
    assert aligned_train.loc[1, "varying"] == 2.0
    assert aligned_test.loc[0, "varying"] == 2.0
    assert aligned_test["train_only"].isna().all()
