from __future__ import annotations

import hashlib
import html
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

PLOT_GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "exposure",
        "Exposure / 多重共線性",
        ("exposure-correlation", "exposure-stability", "exposure-vif", "exposure-condition-number"),
    ),
    ("cross-sectional", "Cross-sectional regression / 横断回帰", ("cs-adjusted-r2", "cs-t-stat-exceedance")),
    (
        "factor",
        "Factor dynamics / 因子挙動",
        ("factor-cumulative-returns", "factor-forecast-correlation", "factor-forecast-volatilities"),
    ),
    (
        "idiosyncratic",
        "Idiosyncratic diagnostics / 残差診断",
        (
            "idio-calibration",
            "idio-vol-ic",
            "idio-tail-rate",
            "idio-kurtosis",
            "idio-skewness",
            "idio-vol-residual-dependence",
        ),
    ),
)

OVERVIEW_PLOTS: tuple[str, ...] = (
    "exposure-correlation",
    "cs-adjusted-r2",
    "factor-cumulative-returns",
    "idio-calibration",
    "idio-vol-ic",
    "idio-vol-residual-dependence",
)

_PAYLOAD_KEY = "_plotly_json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _figure_artifact(
    fig: Any,
    *,
    fold: int | None,
    kind: str,
    plot: str,
    method: str,
) -> dict[str, object]:
    if not hasattr(fig, "to_json"):
        raise TypeError(f"plot did not return a Plotly figure: {plot}")
    payload = str(fig.to_json())
    if not payload:
        raise AssertionError(f"empty Plotly payload: {plot}")
    payload_bytes = payload.encode("utf-8")
    key = f"fold{fold}-{plot}" if fold is not None else plot
    return {
        "fold": fold,
        "kind": kind,
        "plot": plot,
        "method": method,
        "key": key,
        "relative_path": f"index.html#{key}",
        "sha256": hashlib.sha256(payload_bytes).hexdigest(),
        "size_bytes": len(payload_bytes),
        _PAYLOAD_KEY: payload,
    }


def export_factor_model_plots(
    factor_model: Any,
    output_dir: Path,
    *,
    fold_index: int,
) -> list[dict[str, object]]:
    del output_dir
    artifacts: list[dict[str, object]] = []
    for slug, method_name, kwargs in PLOT_CALLS:
        method = getattr(factor_model, method_name, None)
        if method is None:
            raise AttributeError(f"skfolio {SKFOLIO_VERSION} FactorModel is missing {method_name}")
        artifacts.append(
            _figure_artifact(
                method(**kwargs),
                fold=fold_index,
                kind="skfolio-factor-model-plot",
                plot=slug,
                method=method_name,
            )
        )
    return artifacts


def export_oos_comparison_plots(
    summary: dict[str, object],
    output_dir: Path,
) -> list[dict[str, object]]:
    del output_dir
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
        artifacts.append(
            _figure_artifact(
                fig,
                fold=None,
                kind="oos-direct-metric-plot",
                plot=slug,
                method="plotly.graph_objects.Bar",
            )
        )
    return artifacts


def _public_artifact(item: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in item.items() if key != _PAYLOAD_KEY}


def write_plot_manifest(
    output_dir: Path,
    *,
    summary_sha256: str,
    model_contract_sha256: str,
    artifacts: list[dict[str, object]],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "investor2.skfolio-characteristics-plots.v2",
        "skfolio_version": SKFOLIO_VERSION,
        "summary_sha256": summary_sha256,
        "model_contract_sha256": model_contract_sha256,
        "plot_count": len(artifacts),
        "physical_files": ["index.html", "plot-manifest.json"],
        "artifacts": [_public_artifact(item) for item in artifacts],
        "claim_boundary": (
            "Diagnostic visualization only. Plot appearance does not establish alpha, expected-return, "
            "strategy-performance, or covariance-forecast improvement."
        ),
    }
    path = output_dir / "plot-manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _artifact_key(item: dict[str, object]) -> str:
    value = item.get("key")
    if not isinstance(value, str) or not value:
        raise TypeError("artifact key must be a non-empty string")
    return value


def _payload_map(artifacts: list[dict[str, object]]) -> dict[str, object]:
    payloads: dict[str, object] = {}
    for item in artifacts:
        payload = item.get(_PAYLOAD_KEY)
        if not isinstance(payload, str):
            raise TypeError(f"missing Plotly payload for {_artifact_key(item)}")
        payloads[_artifact_key(item)] = json.loads(payload)
    return payloads


def _artifact_map(artifacts: list[dict[str, object]]) -> dict[tuple[int | None, str], dict[str, object]]:
    mapped: dict[tuple[int | None, str], dict[str, object]] = {}
    for item in artifacts:
        fold_value = item.get("fold")
        fold = fold_value if isinstance(fold_value, int) else None
        mapped[(fold, str(item["plot"]))] = item
    return mapped


def _plot_button(item: dict[str, object] | None, label: str) -> str:
    if item is None:
        return '<span class="missing">—</span>'
    key = html.escape(_artifact_key(item), quote=True)
    return f'<a class="plot-link" href="#{key}">{html.escape(label)}</a>'


def _plot_card(item: dict[str, object] | None, title: str) -> str:
    if item is None:
        return ""
    key = html.escape(_artifact_key(item), quote=True)
    return (
        f'<article class="plot-card" id="{key}">'
        f'<div class="plot-head"><strong>{html.escape(title)}</strong></div>'
        f'<div class="plot" data-plot-key="{key}">Loading…</div>'
        "</article>"
    )


def write_plot_index(output_dir: Path, artifacts: list[dict[str, object]]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    by_key = _artifact_map(artifacts)
    oos_items = [item for item in artifacts if item.get("kind") == "oos-direct-metric-plot"]
    factor_items = [item for item in artifacts if item.get("kind") == "skfolio-factor-model-plot"]
    fold_count = len({item.get("fold") for item in factor_items if isinstance(item.get("fold"), int)})

    rows: list[str] = []
    for _group_slug, group_label, slugs in PLOT_GROUPS:
        for index, slug in enumerate(slugs):
            group_cell = (
                f'<td class="group" rowspan="{len(slugs)}">{html.escape(group_label)}</td>' if index == 0 else ""
            )
            method_name = next(method for candidate, method, _ in PLOT_CALLS if candidate == slug)
            rows.append(
                "<tr>"
                f"{group_cell}"
                f"<td><strong>{html.escape(slug)}</strong><small>{html.escape(method_name)}</small></td>"
                f"<td>{_plot_button(by_key.get((0, slug)), 'Fold 0')}</td>"
                f"<td>{_plot_button(by_key.get((1, slug)), 'Fold 1')}</td>"
                "</tr>"
            )

    cards: list[str] = []
    cards.extend(_plot_card(item, str(item["plot"]).removeprefix("oos-").replace("-", " ")) for item in oos_items)
    for slug in OVERVIEW_PLOTS:
        cards.append(_plot_card(by_key.get((0, slug)), f"{slug} · Fold 0"))
        cards.append(_plot_card(by_key.get((1, slug)), f"{slug} · Fold 1"))
    shown = {_artifact_key(item) for item in oos_items}
    shown.update(
        _artifact_key(item)
        for slug in OVERVIEW_PLOTS
        for item in (by_key.get((0, slug)), by_key.get((1, slug)))
        if item is not None
    )
    cards.extend(
        _plot_card(item, f"{item['plot']} · Fold {item['fold']}")
        for item in factor_items
        if _artifact_key(item) not in shown
    )

    payload_json = json.dumps(_payload_map(artifacts), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    style = """
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f6f7f9; color: #16181d; }
    header { padding: 32px clamp(18px, 5vw, 64px) 22px; background: #fff; border-bottom: 1px solid #dfe3e8; }
    h1 { margin: 0 0 8px; font-size: clamp(26px, 4vw, 42px); }
    p { line-height: 1.6; }
    .meta { display: flex; flex-wrap: wrap; gap: 8px; }
    .chip { padding: 6px 10px; border: 1px solid #cfd5dc; border-radius: 999px; font-size: 13px; }
    main { width: min(1500px, calc(100% - 28px)); margin: 0 auto; padding: 26px 0 60px; }
    .matrix-wrap { overflow-x: auto; background: #fff; border: 1px solid #dfe3e8; border-radius: 12px; }
    table { width: 100%; min-width: 720px; border-collapse: collapse; }
    th, td { padding: 11px 13px; text-align: left; border-bottom: 1px solid #e7eaee; }
    td.group { width: 190px; background: #fafbfc; font-weight: 700; }
    td small { display: block; color: #6b7280; font-family: ui-monospace, monospace; font-size: 11px; }
    .plot-link { display: inline-block; padding: 6px 10px; border: 1px solid #bfc7d1; border-radius: 8px; text-decoration: none; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 440px), 1fr)); gap: 14px; margin-top: 20px; }
    .plot-card { min-width: 0; background: #fff; border: 1px solid #dfe3e8; border-radius: 12px; overflow: hidden; scroll-margin-top: 12px; }
    .plot-head { padding: 10px 12px; border-bottom: 1px solid #e7eaee; font-size: 13px; }
    .plot { width: 100%; min-height: 320px; }
    .claim { padding: 13px 15px; background: #fff7db; border-left: 4px solid #b47b00; }
    """

    script = """
    const payloads = JSON.parse(document.getElementById("plot-data").textContent);
    const render = (node) => {
      if (node.dataset.rendered) return;
      const key = node.dataset.plotKey;
      const fig = payloads[key];
      if (!fig) { node.textContent = "Missing plot payload"; return; }
      node.textContent = "";
      Plotly.newPlot(node, fig.data || [], fig.layout || {}, {responsive: true, displaylogo: false});
      node.dataset.rendered = "1";
    };
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) { render(entry.target); observer.unobserve(entry.target); }
      });
    }, {rootMargin: "600px 0px"});
    document.querySelectorAll(".plot").forEach((node) => observer.observe(node));
    """

    html_text = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>skfolio J-Quants diagnostics</title>
<script src="https://cdn.plot.ly/plotly-4.0.0.min.js"></script>
<style>{style}</style>
</head>
<body>
<header>
<h1>skfolio J-Quants diagnostics</h1>
<p>33 logical plotsを1つのHTMLに集約。OOS比較、15 diagnostics × 2 folds、重要診断を同じページで確認する。</p>
<div class="meta"><span class="chip">{len(artifacts)} plots</span><span class="chip">{fold_count} frozen folds</span><span class="chip">skfolio {html.escape(SKFOLIO_VERSION)}</span><span class="chip">2 physical files</span></div>
</header>
<main>
<p class="claim"><strong>判定境界:</strong> 可視化は診断用。既存OOS verdict <code>empirical_baseline_better_or_equal_on_both_primary_risk_metrics</code> を上書きしない。</p>
<h2>15 diagnostics × 2 folds</h2>
<div class="matrix-wrap"><table><thead><tr><th>Category</th><th>Diagnostic</th><th>Fold 0</th><th>Fold 1</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
<h2>Plots</h2>
<div class="grid">{"".join(cards)}</div>
</main>
<script id="plot-data" type="application/json">{payload_json}</script>
<script>{script}</script>
</body>
</html>
"""
    path = output_dir / "index.html"
    path.write_text(html_text, encoding="utf-8")
    return path
