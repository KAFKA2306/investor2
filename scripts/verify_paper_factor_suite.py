#!/usr/bin/env python3
"""Run frozen post-publication factor tests for a registry of classic papers.

The suite distinguishes direct factor-return tests from implementation proxies.
It is a reproducible research gate, not evidence that any series is directly
tradable or that a factor return is an abnormal return after risk adjustment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Metrics:
    start: str
    end: str
    months: int
    annualized_arithmetic_mean: float
    annualized_volatility: float
    annualized_sharpe_zero_rf: float
    cagr: float
    cumulative_return: float
    max_drawdown: float
    positive_month_fraction: float
    iid_t_stat: float
    newey_west_t_stat_lag_6: float
    block_bootstrap_95pct_mean_ci: list[float] | None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def month_key(value: str) -> str:
    if len(value) < 7 or value[4] != "-":
        raise ValueError(f"invalid month: {value}")
    return value[:7]


def load_factor(path: Path, column: str) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        if "date" not in fields or column not in fields:
            raise ValueError(f"{path}: expected date and {column}, got {reader.fieldnames}")
        for row in reader:
            rows.append((month_key(row["date"]), float(row[column]) / 100.0))
    if not rows:
        raise ValueError(f"{path}: no rows")
    months = [date for date, _ in rows]
    if months != sorted(months) or len(set(months)) != len(months):
        raise ValueError(f"{path}: months must be unique and chronological")
    return rows


def select(
    rows: Sequence[tuple[str, float]], start: str, end: str
) -> list[tuple[str, float]]:
    selected = [(date, value) for date, value in rows if start <= date <= end]
    if not selected:
        raise ValueError(f"no observations in range {start} to {end}")
    return selected


def newey_west_t_stat(values: Sequence[float], lags: int = 6) -> float:
    n = len(values)
    mean = sum(values) / n
    centered = [value - mean for value in values]
    gamma0 = sum(value * value for value in centered) / n
    long_run_variance = gamma0
    for lag in range(1, min(lags, n - 1) + 1):
        covariance = (
            sum(centered[index] * centered[index - lag] for index in range(lag, n))
            / n
        )
        weight = 1.0 - lag / (lags + 1.0)
        long_run_variance += 2.0 * weight * covariance
    if long_run_variance <= 0:
        raise ValueError("non-positive Newey-West long-run variance")
    return mean / math.sqrt(long_run_variance / n)


def moving_block_mean_ci(
    values: Sequence[float],
    block_length: int = 12,
    repetitions: int = 20_000,
    seed: int = 2306,
) -> list[float]:
    n = len(values)
    if n < block_length:
        raise ValueError("sample shorter than block length")
    random_generator = random.Random(seed)
    starts = list(range(n - block_length + 1))
    blocks_needed = math.ceil(n / block_length)
    annualized_means: list[float] = []
    for _ in range(repetitions):
        sample: list[float] = []
        for _ in range(blocks_needed):
            start = random_generator.choice(starts)
            sample.extend(values[start : start + block_length])
        annualized_means.append(12.0 * sum(sample[:n]) / n)
    annualized_means.sort()
    return [
        annualized_means[int(0.025 * repetitions)],
        annualized_means[int(0.975 * repetitions) - 1],
    ]


def calculate_metrics(
    rows: Sequence[tuple[str, float]],
    *,
    bootstrap: bool = True,
    bootstrap_seed: int = 2306,
) -> Metrics:
    values = [value for _, value in rows]
    n = len(values)
    mean = sum(values) / n
    variance = sum((value - mean) ** 2 for value in values) / (n - 1)
    monthly_volatility = math.sqrt(variance)
    annualized_mean = 12.0 * mean
    annualized_volatility = math.sqrt(12.0) * monthly_volatility
    wealth = 1.0
    peak = 1.0
    max_drawdown = 0.0
    for value in values:
        wealth *= 1.0 + value
        peak = max(peak, wealth)
        max_drawdown = min(max_drawdown, wealth / peak - 1.0)
    standard_error = monthly_volatility / math.sqrt(n)
    return Metrics(
        start=rows[0][0],
        end=rows[-1][0],
        months=n,
        annualized_arithmetic_mean=annualized_mean,
        annualized_volatility=annualized_volatility,
        annualized_sharpe_zero_rf=annualized_mean / annualized_volatility,
        cagr=wealth ** (12.0 / n) - 1.0,
        cumulative_return=wealth - 1.0,
        max_drawdown=max_drawdown,
        positive_month_fraction=sum(value > 0 for value in values) / n,
        iid_t_stat=mean / standard_error,
        newey_west_t_stat_lag_6=newey_west_t_stat(values, lags=6),
        block_bootstrap_95pct_mean_ci=(
            moving_block_mean_ci(values, seed=bootstrap_seed) if bootstrap else None
        ),
    )


def subtract_monthly_cost(
    rows: Iterable[tuple[str, float]], monthly_cost_bps: int
) -> list[tuple[str, float]]:
    cost = monthly_cost_bps / 10_000.0
    return [(date, value - cost) for date, value in rows]


def verdict(
    implementation: str,
    full: Metrics,
    late: Metrics,
    cost_25: Metrics,
) -> str:
    ci = full.block_bootstrap_95pct_mean_ci
    survives = (
        full.newey_west_t_stat_lag_6 >= 1.96
        and ci is not None
        and ci[0] > 0.0
        and late.annualized_arithmetic_mean > 0.0
        and cost_25.annualized_arithmetic_mean > 0.0
    )
    if implementation == "proxy":
        return "proxy_supportive" if survives else "proxy_not_confirmed"
    if implementation == "factor":
        return "confirmed" if survives else "not_confirmed"
    raise ValueError(f"unknown implementation: {implementation}")


def build_report(
    registry_path: Path,
    *,
    publication_start: str | None = None,
    publication_end: str | None = None,
    bootstrap_seed: int = 2306,
) -> dict[str, object]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    repository_root = registry_path.parents[2]
    datasets = registry["datasets"]
    loaded: dict[tuple[str, str], list[tuple[str, float]]] = {}
    dataset_audit: dict[str, object] = {}

    for dataset_id, dataset in datasets.items():
        path = repository_root / dataset["path"]
        actual_hash = sha256(path)
        if actual_hash != dataset["sha256"]:
            raise ValueError(
                f"{dataset_id}: SHA-256 mismatch, expected {dataset['sha256']}, "
                f"got {actual_hash}"
            )
        dataset_audit[dataset_id] = {
            **dataset,
            "actual_sha256": actual_hash,
        }

    studies: dict[str, object] = {}
    studies_to_run = [
        study
        for study in registry["studies"]
        if (publication_start is None or study["publication_month"] >= publication_start)
        and (publication_end is None or study["publication_month"] <= publication_end)
    ]
    if not studies_to_run:
        raise ValueError("no studies matched the publication window")

    for study in studies_to_run:
        dataset_id = study["dataset"]
        column = study["column"]
        cache_key = (dataset_id, column)
        if cache_key not in loaded:
            path = repository_root / datasets[dataset_id]["path"]
            loaded[cache_key] = load_factor(path, column)
        full_rows = select(
            loaded[cache_key], study["oos_start"], study["oos_end"]
        )
        split = len(full_rows) // 2
        early_rows = full_rows[:split]
        late_rows = full_rows[split:]
        full = calculate_metrics(full_rows, bootstrap_seed=bootstrap_seed)
        early = calculate_metrics(early_rows, bootstrap_seed=bootstrap_seed)
        late = calculate_metrics(late_rows, bootstrap_seed=bootstrap_seed)
        cost_sensitivity = {
            str(cost): asdict(
                calculate_metrics(
                    subtract_monthly_cost(full_rows, cost), bootstrap=False
                )
            )
            for cost in (0, 10, 25, 50)
        }
        studies[study["id"]] = {
            **study,
            "gross_results": {
                "full_oos": asdict(full),
                "early_half": asdict(early),
                "late_half": asdict(late),
            },
            "monthly_haircut_sensitivity_bps": cost_sensitivity,
            "verdict": verdict(
                study["implementation"],
                full,
                late,
                Metrics(**cost_sensitivity["25"]),
            ),
        }

    return {
        "suite": "classic paper post-publication factor tests",
        "method": {
            "split": "chronological midpoint with no tuning",
            "newey_west_lags": 6,
            "block_bootstrap": {
                "repetitions": 20_000,
                "block_months": 12,
                "seed": 2306,
            },
            "confirmation_gate": (
                "Newey-West t >= 1.96; full block-bootstrap lower bound > 0; "
                "late-half annual arithmetic mean > 0; and full mean after a "
                "mechanical 25 bps monthly haircut > 0"
            ),
            "cost_warning": (
                "The monthly haircut is a sensitivity test, not an estimate of "
                "realized turnover, borrow, spread, market impact, or taxes."
            ),
        },
        "publication_filter": {
            "start": publication_start,
            "end": publication_end,
        },
        "datasets": dataset_audit,
        "studies": studies,
    }


def pct(value: float) -> str:
    return f"{100.0 * value:.2f}%"


def render_markdown(report: dict[str, object]) -> str:
    studies = report["studies"]
    lines = [
        "# Multi-paper post-publication OOS factor suite",
        "",
        "This suite adds four classic papers and seven paper–factor hypotheses to the",
        "existing Jegadeesh–Titman momentum test. Proxy rows are not exact",
        "security-level replications and are never treated as independent factor evidence.",
        "",
        "## Results",
        "",
        "| Test | Window | Months | Annual mean | Sharpe | CAGR | Max drawdown | NW t | 95% block CI | Late-half mean | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for study in studies.values():
        full = study["gross_results"]["full_oos"]
        late = study["gross_results"]["late_half"]
        ci = full["block_bootstrap_95pct_mean_ci"]
        lines.append(
            "| {id} | {start}–{end} | {months} | {mean} | {sharpe:.2f} | "
            "{cagr} | {mdd} | {nw:.2f} | {lo} to {hi} | {late} | `{verdict}` |".format(
                id=study["id"],
                start=full["start"],
                end=full["end"],
                months=full["months"],
                mean=pct(full["annualized_arithmetic_mean"]),
                sharpe=full["annualized_sharpe_zero_rf"],
                cagr=pct(full["cagr"]),
                mdd=pct(full["max_drawdown"]),
                nw=full["newey_west_t_stat_lag_6"],
                lo=pct(ci[0]),
                hi=pct(ci[1]),
                late=pct(late["annualized_arithmetic_mean"]),
                verdict=study["verdict"],
            )
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- None of the seven new hypotheses passes the locked confirmation gate.",
            "- SMB and HML have weak full-window means and fail the 25 bps monthly-haircut stress test.",
            "- HML's late-half mean is negative in both its 1992 proxy and 1993 factor tests.",
            "- RMW is positive in the short 2015–2020 window and its block-bootstrap lower bound is positive, but its Newey–West t-statistic is below 1.96 and the 25 bps monthly-haircut stress test is negative.",
            "- CMA is negative in both the full and late windows.",
            "- These results are factor-return tests. They do not reproduce the original papers' security-level cross-sectional regressions.",
            "",
            "## Reproduction",
            "",
            "```bash",
            "python scripts/verify_paper_factor_suite.py \\",
            "  --registry docs/research/paper_factor_registry.json \\",
            "  --json-output docs/research/multi_paper_oos_results.json \\",
            "  --markdown-output docs/research/multi_paper_oos_summary.md",
            "",
            "python -m pytest -q tests/test_paper_factor_suite.py",
            "```",
            "",
            "The source mirrors are frozen by commit, blob SHA, and normalized-file SHA-256.",
            "The official Kenneth French pages remain the authority for factor definitions.",
            "",
            "## Limitations",
            "",
            "- The mirror snapshot ends in February 2020; this is not a through-2026 result.",
            "- Banz (1981) is tested only through a delayed SMB proxy window beginning in July 1992.",
            "- The Fama–French (1992) rows use SMB and HML as implementation proxies, not exact replications.",
            "- Factor returns are not abnormal returns and may compensate systematic risk.",
            "- The mechanical monthly haircut is not a strategy-specific transaction-cost model.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("docs/research/paper_factor_registry.json"),
    )
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--markdown-output", type=Path)
    args = parser.parse_args()
    report = build_report(args.registry)
    rendered_json = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered_json, encoding="utf-8")
    else:
        print(rendered_json, end="")
    if args.markdown_output:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(render_markdown(report), encoding="utf-8")


if __name__ == "__main__":
    main()
