from __future__ import annotations

import importlib.util
from pathlib import Path


def load_module():
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts" / "compare_french_factor_revisions.py"
    spec = importlib.util.spec_from_file_location("compare_french_factor_revisions", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_compare_series_reports_revision_magnitude_and_coverage() -> None:
    module = load_module()
    result = module.compare_series(
        [("2020-01", 0.0100), ("2020-02", -0.0200), ("2020-03", 0.0300)],
        [("2020-01", 0.0101), ("2020-02", -0.0200), ("2020-03", 0.0298)],
    )

    assert result["months"] == 3
    assert result["start"] == "2020-01"
    assert result["end"] == "2020-03"
    assert result["changed_months"] == 2
    assert result["changed_share"] == 2 / 3
    assert abs(result["mean_revision_bps"] - (-1 / 3)) < 1e-9
    assert abs(result["mean_abs_revision_bps"] - 1.0) < 1e-9
    assert abs(result["max_abs_revision_bps"] - 2.0) < 1e-9


def test_compare_series_uses_only_overlap() -> None:
    module = load_module()
    result = module.compare_series(
        [("2019-12", 0.01), ("2020-01", 0.02)],
        [("2020-01", 0.02), ("2020-02", 0.03)],
    )
    assert result["months"] == 1
    assert result["start"] == "2020-01"
    assert result["end"] == "2020-01"
    assert result["changed_months"] == 0
