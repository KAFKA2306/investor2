from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.research.skfolio_characteristics import asset_panel_from_prices, build_price_only_characteristics_model
from src.research.skfolio_plot_exports import (
    PLOT_CALLS,
    export_factor_model_plots,
    export_oos_comparison_plots,
    write_plot_index,
    write_plot_manifest,
)


def _fitted_factor_model():
    n_observations = 260
    n_assets = 35
    time = np.arange(n_observations, dtype=float)
    prices: dict[str, np.ndarray] = {}
    for asset in range(n_assets):
        simple_returns = (
            0.0002
            + 0.003 * np.sin((time + asset * 0.7) / (8.0 + asset % 5))
            + 0.0015 * np.cos((time * (1.0 + asset / 100.0)) / 13.0)
        )
        prices[f"A{asset:02d}"] = 100.0 * np.cumprod(1.0 + simple_returns)
    price_frame = pd.DataFrame(
        prices,
        index=pd.date_range("2025-01-01", periods=n_observations, freq="B"),
    )
    panel = asset_panel_from_prices(price_frame)
    returns = pd.DataFrame(
        panel["returns"],
        index=pd.DatetimeIndex(panel.observations),
        columns=[str(name) for name in panel.asset_names],
    )
    model = build_price_only_characteristics_model()
    model.fit(X=returns, characteristics=panel)
    return model.factor_model_


def _oos_summary() -> dict[str, object]:
    return {
        "aggregate": {
            "mean_baseline_empirical_covariance": {
                "normalized_frobenius_error": 0.57,
                "equal_weight_volatility_absolute_error": 0.021,
                "diagonal_variance_mae": 0.00033,
            },
            "mean_skfolio_characteristics_covariance": {
                "normalized_frobenius_error": 0.65,
                "equal_weight_volatility_absolute_error": 0.027,
                "diagonal_variance_mae": 0.00034,
            },
        }
    }


def test_pinned_skfolio_factor_model_exposes_all_required_plot_methods() -> None:
    factor_model = _fitted_factor_model()
    for _, method_name, _ in PLOT_CALLS:
        assert callable(getattr(factor_model, method_name))


def test_compact_export_keeps_33_logical_plots_in_two_physical_files(tmp_path: Path) -> None:
    factor_model = _fitted_factor_model()
    artifacts = []
    artifacts.extend(export_factor_model_plots(factor_model, tmp_path, fold_index=0))
    artifacts.extend(export_factor_model_plots(factor_model, tmp_path, fold_index=1))
    artifacts.extend(export_oos_comparison_plots(_oos_summary(), tmp_path))

    assert len(artifacts) == len(PLOT_CALLS) * 2 + 3
    assert list(tmp_path.iterdir()) == []

    manifest_path = write_plot_manifest(
        tmp_path,
        summary_sha256="a" * 64,
        model_contract_sha256="b" * 64,
        artifacts=artifacts,
    )
    index_path = write_plot_index(tmp_path, artifacts)

    assert {path.name for path in tmp_path.iterdir()} == {"index.html", "plot-manifest.json"}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "investor2.skfolio-characteristics-plots.v2"
    assert manifest["plot_count"] == 33
    assert manifest["physical_files"] == ["index.html", "plot-manifest.json"]
    assert manifest["skfolio_version"] == "1.0.0"
    assert all("_plotly_json" not in item for item in manifest["artifacts"])
    assert all(str(item["relative_path"]).startswith("index.html#") for item in manifest["artifacts"])

    index_html = index_path.read_text(encoding="utf-8")
    assert "33 logical plots" in index_html
    assert "15 diagnostics × 2 folds" in index_html
    assert "2 physical files" in index_html
    assert "Plotly.newPlot" in index_html
    assert "IntersectionObserver" in index_html
    assert "<iframe" not in index_html
    assert "fold0/exposure-correlation.html" not in index_html

    match = re.search(
        r'<script id="plot-data" type="application/json">(.*?)</script>',
        index_html,
        flags=re.DOTALL,
    )
    assert match is not None
    payloads = json.loads(match.group(1))
    assert len(payloads) == 33
    assert "fold0-exposure-correlation" in payloads
    assert "fold1-idio-vol-ic" in payloads
    assert "oos-normalized-frobenius-error" in payloads


def test_plot_payload_hashes_are_stable_metadata(tmp_path: Path) -> None:
    factor_model = _fitted_factor_model()
    artifacts = export_factor_model_plots(factor_model, tmp_path, fold_index=0)

    assert len(artifacts) == len(PLOT_CALLS)
    for artifact in artifacts:
        assert len(str(artifact["sha256"])) == 64
        size_bytes = artifact["size_bytes"]
        assert isinstance(size_bytes, int)
        assert size_bytes > 0
        assert str(artifact["relative_path"]).startswith("index.html#")
