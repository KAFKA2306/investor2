from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


DEFAULT_INPUT = Path(
    "docs/research/data/kioxia_semiconductor_universe_50_5y_quarterly_2026-08-12.json"
)
TARGET_EDINET_CODE = "E35948"
MAX_PLOTTED_FISCAL_YEAR = 2026


def load_kioxia_series(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("company_count") != 50:
        raise ValueError("expected 50-company canonical universe")
    companies = payload.get("companies")
    if not isinstance(companies, list):
        raise TypeError("companies must be a list")

    company = next(
        (item for item in companies if item.get("edinet_code") == TARGET_EDINET_CODE),
        None,
    )
    if company is None:
        raise ValueError(f"{TARGET_EDINET_CODE} is missing from the snapshot")

    rows = [
        row
        for row in company.get("quarterly", [])
        if row.get("revenue") is not None
        and isinstance(row.get("fiscal_year"), int)
        and row["fiscal_year"] <= MAX_PLOTTED_FISCAL_YEAR
    ]
    rows.sort(key=lambda row: (row["fiscal_year"], row.get("quarter", 0)))
    if not rows:
        raise ValueError("no Kioxia revenue rows available for plotting")
    return payload, rows


def build_chart(rows: list[dict[str, Any]], output: Path) -> None:
    labels = [f"FY{row['fiscal_year']} Q{row['quarter']}" for row in rows]
    revenue_bn = [row["revenue"] / 1_000_000_000 for row in rows]
    operating_bn = [
        (row.get("operating_income") / 1_000_000_000)
        if row.get("operating_income") is not None
        else float("nan")
        for row in rows
    ]

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(labels, revenue_bn, marker="o", linewidth=2, label="Revenue")
    ax.plot(labels, operating_bn, marker="o", linewidth=2, label="Operating income")
    ax.set_title("Kioxia quarterly financial trend")
    ax.set_xlabel("Fiscal quarter")
    ax.set_ylabel("JPY billions")
    ax.grid(axis="y", alpha=0.25)
    ax.legend()
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def build_page(payload: dict[str, Any], rows: list[dict[str, Any]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    chart_path = output_dir / "chart.png"
    build_chart(rows, chart_path)

    table_rows = []
    for row in rows:
        period = f"FY{row['fiscal_year']} Q{row['quarter']}"
        revenue = row["revenue"] / 1_000_000_000
        operating = row.get("operating_income")
        operating_text = "—" if operating is None else f"{operating / 1_000_000_000:,.1f}"
        source_type = html.escape(str(row.get("source_type", "unknown")))
        canonical = "yes" if row.get("canonical_eligible") else "no"
        table_rows.append(
            "<tr>"
            f"<td>{period}</td><td>{revenue:,.1f}</td><td>{operating_text}</td>"
            f"<td>{source_type}</td><td>{canonical}</td>"
            "</tr>"
        )

    summary = {
        "dataset_id": payload.get("dataset_id"),
        "as_of": payload.get("as_of"),
        "edinet_code": TARGET_EDINET_CODE,
        "point_count": len(rows),
        "first_period": f"FY{rows[0]['fiscal_year']} Q{rows[0]['quarter']}",
        "last_period": f"FY{rows[-1]['fiscal_year']} Q{rows[-1]['quarter']}",
        "excluded_periods": [
            {
                "period": "FY2027 Q1",
                "reason": "source row is excluded from the analytical plot pending primary-source revalidation of the discontinuity",
            }
        ],
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    page = f"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kioxia quarterly financial trend</title>
<style>
body{{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;max-width:1100px;margin:0 auto;padding:32px 20px;line-height:1.55;color:#202124}}
h1{{font-size:2rem;margin-bottom:.35rem}} .meta{{color:#5f6368;margin-bottom:1.5rem}} img{{width:100%;height:auto;border:1px solid #dadce0;border-radius:12px}}
.note{{background:#f8f9fa;border-left:4px solid #5f6368;padding:12px 16px;margin:20px 0}} table{{width:100%;border-collapse:collapse;margin-top:24px}} th,td{{text-align:right;padding:9px;border-bottom:1px solid #e0e0e0}} th:first-child,td:first-child,th:nth-child(4),td:nth-child(4){{text-align:left}}
</style>
</head>
<body>
<h1>Kioxia quarterly financial trend</h1>
<div class="meta">FY2025 Q1–FY2026 Q4 · JPY billions · snapshot {html.escape(str(payload.get('as_of')))}</div>
<img src="chart.png" alt="Kioxia quarterly revenue and operating income chart">
<div class="note"><strong>Evidence boundary:</strong> this chart plots fetched quarterly rows for trend inspection. Source type and strict canonical eligibility are shown below. FY2027 Q1 is deliberately excluded pending primary-source revalidation because its value is discontinuous with the preceding series.</div>
<table>
<thead><tr><th>Period</th><th>Revenue (JPY bn)</th><th>Operating income (JPY bn)</th><th>Source type</th><th>Strict canonical</th></tr></thead>
<tbody>{''.join(table_rows)}</tbody>
</table>
</body>
</html>
"""
    (output_dir / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    payload, rows = load_kioxia_series(args.input)
    build_page(payload, rows, args.output_dir)


if __name__ == "__main__":
    main()
