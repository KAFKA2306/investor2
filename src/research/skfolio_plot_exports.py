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


def _artifact_map(artifacts: list[dict[str, object]]) -> dict[tuple[int | None, str], dict[str, object]]:
    mapped: dict[tuple[int | None, str], dict[str, object]] = {}
    for item in artifacts:
        fold_value = item.get("fold")
        fold = fold_value if isinstance(fold_value, int) else None
        mapped[(fold, str(item["plot"]))] = item
    return mapped


def _plot_link(item: dict[str, object] | None, label: str) -> str:
    if item is None:
        return '<span class="missing">—</span>'
    path = html.escape(str(item["relative_path"]), quote=True)
    return f'<a class="plot-link" href="{path}">{html.escape(label)}</a>'


def _plot_preview(item: dict[str, object] | None, title: str) -> str:
    if item is None:
        return ""
    path = html.escape(str(item["relative_path"]), quote=True)
    return (
        '<article class="preview-card">'
        f'<div class="preview-head"><strong>{html.escape(title)}</strong>'
        f'<a href="{path}">全画面で開く ↗</a></div>'
        f'<iframe loading="lazy" title="{html.escape(title, quote=True)}" src="{path}"></iframe>'
        "</article>"
    )


def write_plot_index(output_dir: Path, artifacts: list[dict[str, object]]) -> Path:
    by_key = _artifact_map(artifacts)
    oos_items = [item for item in artifacts if item.get("kind") == "oos-direct-metric-plot"]
    factor_items = [item for item in artifacts if item.get("kind") == "skfolio-factor-model-plot"]
    fold_count = len({item.get("fold") for item in factor_items if isinstance(item.get("fold"), int)})

    oos_cards = "".join(
        _plot_preview(item, str(item["plot"]).removeprefix("oos-").replace("-", " ")) for item in oos_items
    )

    table_rows: list[str] = []
    for group_slug, group_label, slugs in PLOT_GROUPS:
        for index, slug in enumerate(slugs):
            group_cell = f'<td class="group" rowspan="{len(slugs)}">{html.escape(group_label)}</td>' if index == 0 else ""
            method_name = next(method for candidate, method, _ in PLOT_CALLS if candidate == slug)
            table_rows.append(
                "<tr>"
                f"{group_cell}"
                f'<td><strong>{html.escape(slug)}</strong><small>{html.escape(method_name)}</small></td>'
                f'<td>{_plot_link(by_key.get((0, slug)), "Fold 0")}</td>'
                f'<td>{_plot_link(by_key.get((1, slug)), "Fold 1")}</td>'
                f'<td><a class="anchor" href="#{html.escape(group_slug, quote=True)}">{html.escape(group_slug)}</a></td>'
                "</tr>"
            )

    preview_sections: list[str] = []
    for slug in OVERVIEW_PLOTS:
        fold0 = _plot_preview(by_key.get((0, slug)), f"{slug} · Fold 0")
        fold1 = _plot_preview(by_key.get((1, slug)), f"{slug} · Fold 1")
        if fold0 or fold1:
            preview_sections.append(
                f'<section class="diagnostic-preview" id="preview-{html.escape(slug, quote=True)}">'
                f"<h3>{html.escape(slug)}</h3><div class=\"preview-grid\">{fold0}{fold1}</div></section>"
            )

    category_nav = "".join(
        f'<a href="#{html.escape(group_slug, quote=True)}">{html.escape(group_label.split(" / ")[0])}</a>'
        for group_slug, group_label, _ in PLOT_GROUPS
    )
    category_blocks = "".join(
        f'<span id="{html.escape(group_slug, quote=True)}" class="category-anchor"></span>'
        for group_slug, _, _ in PLOT_GROUPS
    )

    style = """
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f6f7f9; color: #16181d; }
    a { color: inherit; }
    header { padding: 34px clamp(18px, 5vw, 64px) 24px; background: #fff; border-bottom: 1px solid #dfe3e8; }
    h1 { margin: 0 0 8px; font-size: clamp(26px, 4vw, 44px); letter-spacing: -0.035em; }
    h2 { margin: 0 0 14px; font-size: 24px; }
    h3 { margin: 24px 0 10px; }
    p { line-height: 1.6; }
    .meta { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }
    .chip { padding: 7px 10px; border: 1px solid #cfd5dc; border-radius: 999px; background: #f9fafb; font-size: 13px; }
    .verdict { margin-top: 18px; padding: 14px 16px; background: #fff7db; border-left: 4px solid #b47b00; max-width: 920px; }
    nav { position: sticky; top: 0; z-index: 10; display: flex; gap: 8px; overflow-x: auto; padding: 10px clamp(18px, 5vw, 64px); background: rgba(255,255,255,.96); border-bottom: 1px solid #dfe3e8; backdrop-filter: blur(10px); }
    nav a { white-space: nowrap; text-decoration: none; padding: 7px 10px; border-radius: 8px; background: #eef1f4; font-size: 13px; }
    main { width: min(1500px, calc(100% - 32px)); margin: 0 auto; padding: 28px 0 60px; }
    section { margin: 0 0 36px; }
    .preview-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(100%, 440px), 1fr)); gap: 14px; }
    .preview-card { min-width: 0; overflow: hidden; background: #fff; border: 1px solid #dfe3e8; border-radius: 12px; }
    .preview-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding: 11px 13px; border-bottom: 1px solid #e7eaee; font-size: 13px; }
    .preview-head a { white-space: nowrap; }
    iframe { display: block; width: 100%; height: 310px; border: 0; background: #fff; }
    .matrix-wrap { overflow-x: auto; background: #fff; border: 1px solid #dfe3e8; border-radius: 12px; }
    table { width: 100%; min-width: 780px; border-collapse: collapse; }
    th, td { padding: 12px 14px; text-align: left; border-bottom: 1px solid #e7eaee; vertical-align: middle; }
    th { position: sticky; top: 51px; z-index: 4; background: #f3f5f7; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
    td.group { width: 190px; background: #fafbfc; font-weight: 700; }
    td small { display: block; margin-top: 3px; color: #6b7280; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 11px; }
    .plot-link { display: inline-block; padding: 7px 11px; border: 1px solid #bfc7d1; border-radius: 8px; text-decoration: none; background: #fff; font-weight: 650; }
    .plot-link:hover { background: #eef2f6; }
    .anchor { color: #606b78; font-size: 12px; }
    .missing { color: #9aa1aa; }
    .category-anchor { scroll-margin-top: 70px; }
    .diagnostic-preview { scroll-margin-top: 70px; }
    footer { padding: 22px clamp(18px, 5vw, 64px); color: #66707c; border-top: 1px solid #dfe3e8; background: #fff; font-size: 13px; }
    @media (max-width: 700px) { main { width: min(100% - 20px, 1500px); } iframe { height: 270px; } th { top: 49px; } }
    """

    html_text = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>skfolio J-Quants diagnostics overview</title>
<style>{style}</style>
</head>
<body>
<header>
<h1>skfolio J-Quants diagnostics</h1>
<p>33 plotsをクリック探索ではなく、OOS結果 → Fold比較 → 重要診断の順に一画面で俯瞰するためのindex。</p>
<div class="meta"><span class="chip">{len(artifacts)} plots</span><span class="chip">{fold_count} frozen folds</span><span class="chip">skfolio {html.escape(SKFOLIO_VERSION)}</span></div>
<div class="verdict"><strong>判定境界:</strong> 可視化は診断用。既存OOS verdict <code>empirical_baseline_better_or_equal_on_both_primary_risk_metrics</code> を上書きしない。</div>
</header>
<nav><a href="#oos">OOS比較</a><a href="#matrix">15×2 Fold比較</a><a href="#key-previews">重要plot</a>{category_nav}</nav>
<main>
<section id="oos"><h2>OOS direct comparison</h2><p>まず性能差を確認。下に進むほどモデル内部の診断。</p><div class="preview-grid">{oos_cards}</div></section>
<section id="matrix"><h2>15 diagnostics × 2 folds</h2><p>同じ診断をFold 0 / Fold 1で横並びに開ける全体マトリクス。</p>{category_blocks}<div class="matrix-wrap"><table><thead><tr><th>Category</th><th>Diagnostic</th><th>Fold 0</th><th>Fold 1</th><th>Group</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div></section>
<section id="key-previews"><h2>重要診断のFold横並びプレビュー</h2><p>最初に見る6診断だけを埋め込み。その他は上の比較表から開く。</p>{''.join(preview_sections)}</section>
</main>
<footer>Derived diagnostic visualization only. Plot appearance does not establish alpha, expected-return, strategy-performance, or covariance-forecast improvement.</footer>
</body>
</html>
"""
    path = output_dir / "index.html"
    path.write_text(html_text, encoding="utf-8")
    return path
