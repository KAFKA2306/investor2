from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

SOURCE_URL = "https://raw.githubusercontent.com/tbrown034/open-cabinet/main/data/officials/trump-donald-j.json"
OGE_GUIDE_URL = "https://www.oge.gov/web/278eGuide.nsf/Form_278-T"
OGE_DEFINITIONS_URL = "https://www.oge.gov/web/278eGuide.nsf/Definitions"
EXPECTED_TYPES = {"Purchase", "Sale"}
LEGACY_OUTPUTS = ("index.html", "trump_daily_transactions.csv")


def load_source(source_url: str = SOURCE_URL, source_file: Path | None = None) -> tuple[dict[str, Any], bytes]:
    if source_file is not None:
        raw = source_file.read_bytes()
    else:
        request = urllib.request.Request(source_url, headers={"User-Agent": "KAFKA2306/investor2 daily chart"})
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS source by default
            raw = response.read()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("source payload must be an object")
    return payload, raw


def aggregate_transactions(payload: dict[str, Any]) -> list[dict[str, int | str]]:
    transactions = payload.get("transactions")
    if not isinstance(transactions, list) or any(not isinstance(row, dict) for row in transactions):
        raise ValueError("transactions must be a list of objects")

    unknown = sorted({str(row.get("type")) for row in transactions if row.get("type") not in EXPECTED_TYPES})
    if unknown:
        raise ValueError(f"unexpected transaction types: {unknown}")

    daily: dict[str, Counter[str]] = defaultdict(Counter)
    for row in transactions:
        date = row.get("date")
        if not isinstance(date, str) or not date:
            raise ValueError("transaction date must be a non-empty string")
        datetime.strptime(date, "%Y-%m-%d")
        daily[date][str(row["type"])] += 1

    return [
        {
            "date": date,
            "Purchase": daily[date]["Purchase"],
            "Sale": daily[date]["Sale"],
            "Total": daily[date]["Purchase"] + daily[date]["Sale"],
        }
        for date in sorted(daily)
    ]


def stable_fetched_at(output_dir: Path, source_hash: str) -> str:
    path = output_dir / "summary.json"
    if path.is_file():
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))
            if previous.get("source_sha256") == source_hash and isinstance(previous.get("fetched_at"), str):
                return previous["fetched_at"]
        except (OSError, json.JSONDecodeError):
            pass
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_outputs(
    payload: dict[str, Any], raw: bytes, rows: list[dict[str, int | str]], output_dir: Path, source_url: str
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(raw).hexdigest()
    fetched_at = stable_fetched_at(output_dir, source_hash)
    for name in LEGACY_OUTPUTS:
        (output_dir / name).unlink(missing_ok=True)

    purchases = [int(row["Purchase"]) for row in rows]
    sales = [int(row["Sale"]) for row in rows]
    dates = [str(row["date"]) for row in rows]
    figure, axis = plt.subplots(figsize=(14, 7))
    axis.bar(dates, purchases, label="Purchase")
    axis.bar(dates, sales, bottom=purchases, label="Sale")
    axis.set(title="Donald J. Trump — disclosed OGE 278-T transaction rows by transaction date", xlabel="Transaction date", ylabel="Number of disclosed transaction rows")
    axis.legend()
    if dates:
        step = max(1, len(dates) // 12)
        for index, label in enumerate(axis.get_xticklabels()):
            label.set_visible(index % step == 0 or index == len(dates) - 1)
            label.set_rotation(45)
            label.set_ha("right")
    figure.tight_layout()
    figure.savefig(output_dir / "trump_daily_transactions.png", dpi=150, metadata={"Software": "investor2"})
    plt.close(figure)

    max_row = max(rows, key=lambda row: int(row["Total"])) if rows else None
    summary = {
        "schema_version": "investor2.trump-daily-278t-chart.v2",
        "name": payload.get("name"),
        "filingType": payload.get("filingType"),
        "mostRecentFilingDate": payload.get("mostRecentFilingDate"),
        "lastIngestedDate": payload.get("lastIngestedDate"),
        "source_url": source_url,
        "source_type": "derived_parser_output",
        "primary_evidence": [OGE_GUIDE_URL, OGE_DEFINITIONS_URL],
        "fetched_at": fetched_at,
        "source_sha256": source_hash,
        "row_count": sum(int(row["Total"]) for row in rows),
        "purchase_rows": sum(purchases),
        "sale_rows": sum(sales),
        "daily_points": len(rows),
        "max_daily_total": int(max_row["Total"]) if max_row else 0,
        "max_daily_total_date": max_row["date"] if max_row else None,
        "unit": "number of disclosed transaction rows",
        "caveat": "Count of rows in derived parser output for disclosed OGE Form 278-T transactions; not an OGE-published aggregate and does not prove the filer personally placed each order.",
        "daily": rows,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-url", default=SOURCE_URL)
    parser.add_argument("--source-file", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("generated/trump-daily-chart"))
    args = parser.parse_args()
    payload, raw = load_source(args.source_url, args.source_file)
    summary = write_outputs(payload, raw, aggregate_transactions(payload), args.output_dir, args.source_url)
    print(json.dumps({key: summary[key] for key in ("row_count", "purchase_rows", "sale_rows", "daily_points", "source_sha256")}))


if __name__ == "__main__":
    main()
