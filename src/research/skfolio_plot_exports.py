from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import plotly.graph_objects as go

from src.research.skfolio_characteristics import SKFOLIO_VERSION

PLOT_CALLS: tuple[tuple[str, str, dict[str, object]], ...] = (
    ("exposure-correlation", "plot_exposure_correlation", {}),
    ("exposure-stability", "plot_exposure_stability", {}),
    ("exposure-vif", "plot_exposure_vif", {}),
    ("exposure-condition-number", "plot_exposure_condition_number", {}),
    ("cs-adjusted-r2", "plot_cs_regression_scores", {"score": "adjusted_r2", "window": 20}),
    ("cs-t-stat-exceedance", "plot_cs_regression_t_stat_exceedance_rate", {}),
    ("factor-cumulative-returns", "plot_factor_cumulative_returns", {}),
    ("factor-forecast-correlation", "plot_factor_forecast_correlation", {}),
    ("factor-forecast-volatilities", "plot_factor_forecast_volatilities", {}),
    ("idio-calibration", "plot_idio_calibration", {"window": 20}),
    ("idio-vol-ic", "plot_idio_vol_ic", {}),
    ("idio-tail-rate", "plot_idio_tail_rate", {}),
    ("idio-kurtosis", "plot_idio_kurtosis", {}),
    ("idio-skewness", "plot_idio_skewness", {}),
    ("idio-vol-residual-dependence", "plot_idio_vol_residual_dependence", {}),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_figure(fig: Any, path: Path) -> None:
    if not hasattr(fig, "write_html"):
        raise TypeError(f"skfolio plot did not return a Plotly figure: {path.name}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(path, include_plotlyjs="cdn", full_html=True)
    if not path.exists() or path.stat().st_size == 0:
        raise AssertionError(f"plot was not written: {path}")


def export_factor_model_plots(factor_model: Any, output_dir: Path, *, fold_index: int) -> list[dict[str, object]]:
    fold_dir = output_dir / f"fold{fold_index}"
    artifacts: list[dict[str, object]] = []
    for slug, method_name, kwargs in PLOT_CALLS:
        method = getattr(factor_model, method_name, None)
        if method is None:
            raise AttributeError(f"skfolio {SKFOLIO_VERSION} FactorModel is missing {method_name}")
        fig = method(**kwargs)
        path = fold_dir / f"{slug}.html"
        _write_figure(fig, path)
        artifacts.append(
            {
                "fold": fold_index,
                "kind": "skfolio-factor-model-plot",
                "plot": slug,
                "method": method_name,
                "relative_path": path.relative_to(output_dir).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return artifacts


def export_oos_comparison_plots(summary: dict[str, object], output_dir: Path) -> list[dict[str, object]]:
    aggregate = summary["aggregate"]
    if not isinstance(aggregate, dict):
        raise TypeError("summary aggregate must be an object")
    baseline = aggregate["mean_baseline_empirical_covariance"]
    candidate = aggregate["mean_skfolio_characteristics_covariance"]
    if not isinstance(baseline, dict) or not isinstance(candidate, dict):
        raise TypeError("summary covariance aggregates must be objects")

    specs = (
        (
            "oos-normalized-frobenius-error",
            "normalized_frobenius_error",
            "Mean OOS normalized Frobenius error",
        ),
        (
            "oos-equal-weight-volatility-error",
            "equal_weight_volatility_absolute_error",
            "Mean OOS equal-weight volatility absolute error",
        ),
        (
            "oos-diagonal-variance-mae",
            "diagonal_variance_mae",
            "Mean OOS diagonal variance MAE",
        ),
    )
    artifacts: list[dict[str, object]] = []
    for slug, metric, title in specs:
        fig = go.Figure(
            data=[
                go.Bar(
                    x=["Empirical covariance", "skfolio characteristics"],
                    y=[float(baseline[metric]), float(candidate[metric])],
                )
            ]
        )
        fig.update_layout(title=title, yaxis_title=metric.replace("_", " "))
        path = output_dir / f"{slug}.html"
        _write_figure(fig, path)
        artifacts.append(
            {
                "fold": None,
                "kind": "oos-direct-metric-plot",
                "plot": slug,
                "method": "plotly.graph_objects.Bar",
                "relative_path": path.relative_to(output_dir).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return artifacts


def write_plot_manifest(
    output_dir: Path,
    *,
    summary_sha256: str,
    model_contract_sha256: str,
    artifacts: list[dict[str, object]],
) -> Path:
    manifest = {
        "schema_version": "investor2.skfolio-characteristics-plots.v1",
        "skfolio_version": SKFOLIO_VERSION,
        "summary_sha256": summary_sha256,
        "model_contract_sha256": model_contract_sha256,
        "plot_count": len(artifacts),
        "artifacts": artifacts,
        "claim_boundary": (
            "Diagnostic visualization only. Plot appearance does not establish alpha, expected-return, "
            "strategy-performance, or covariance-forecast improvement."
        ),
    }
    path = output_dir / "plot-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def write_plot_index(output_dir: Path, artifacts: list[dict[str, object]]) -> Path:
    links = "\n".join(
        f'<li><a href="{item["relative_path"]}">{item["plot"]}</a>' for item in artifacts
    )
    html = (
        "<!doctype html><html><head><meta charset=\"utf-8\"><title>skfolio J-Quants diagnostics</title></head>"
        "<body><h1>skfolio J-Quants diagnostics</h1>"
        "<p>Derived diagnostic plots. The OOS verdict remains authoritative in summary.json.</p>"
        f"<ul>{links}</ul></body></html>\n"
    )
    path = output_dir / "index.html"
    path.write_text(html, encoding="utf-8")
    return path
