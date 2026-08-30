from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.research.skfolio_characteristics import asset_panel_from_prices, build_price_only_characteristics_model
from src.research.skfolio_plot_exports import (
    PLOT_CALLS,
    export_factor_model_plots,
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


def test_pinned_skfolio_factor_model_exposes_all_required_plot_methods() -> None:
    factor_model = _fitted_factor_model()
    for _, method_name, _ in PLOT_CALLS:
        assert callable(getattr(factor_model, method_name))


def test_export_factor_model_plots_writes_interactive_html_and_manifest(tmp_path: Path) -> None:
    factor_model = _fitted_factor_model()
    artifacts = export_factor_model_plots(factor_model, tmp_path, fold_index=0)

    assert len(artifacts) == len(PLOT_CALLS)
    for artifact in artifacts:
        path = tmp_path / str(artifact["relative_path"])
        assert path.exists()
        assert path.suffix == ".html"
        assert path.stat().st_size > 0
        assert len(str(artifact["sha256"])) == 64

    manifest_path = write_plot_manifest(
        tmp_path,
        summary_sha256="a" * 64,
        model_contract_sha256="b" * 64,
        artifacts=artifacts,
    )
    index_path = write_plot_index(tmp_path, artifacts)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["plot_count"] == len(PLOT_CALLS)
    assert manifest["skfolio_version"] == "1.0.0"
    assert index_path.exists()
    assert "factor-cumulative-returns" in index_path.read_text(encoding="utf-8")
