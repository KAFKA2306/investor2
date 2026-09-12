#!/usr/bin/env python3
from __future__ import annotations

import argparse
import calendar
import html
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WATCHLIST = ROOT / "config/japan_yen_watchlist.json"
DEFAULT_OUTPUT_DIR = ROOT / "data/snapshots"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 Chrome/153 Safari/537.36"
)
DISCLOSURE_KEYWORDS = (
    "決算",
    "業績修正",
    "上方修正",
    "下方修正",
    "配当",
    "増配",
    "減配",
    "決算短信",
)


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = html.unescape(data).strip()
        if value:
            self.parts.append(value)

    def text(self) -> str:
        return "\n".join(self.parts)


@dataclass(frozen=True)
class Observation:
    observed_date: date
    close: float
    volume: int | None


def iso_now() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_yahoo_ticker(ticker: str) -> str:
    if ticker == "JPY=X":
        return ticker
    if not re.fullmatch(r"\d{4}\.T", ticker):
        raise ValueError(f"Japanese equity ticker must use ####.T form: {ticker}")
    return ticker


def subtract_months(day: date, months: int) -> date:
    if months < 0:
        raise ValueError("months must be non-negative")
    month_index = day.year * 12 + (day.month - 1) - months
    year, zero_based_month = divmod(month_index, 12)
    month = zero_based_month + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))


def parse_yahoo_chart(payload: dict[str, Any]) -> list[Observation]:
    chart = payload.get("chart")
    if not isinstance(chart, dict) or chart.get("error"):
        raise ValueError(f"Yahoo chart response error: {chart.get('error') if isinstance(chart, dict) else chart}")
    result = chart.get("result")
    if not isinstance(result, list) or not result:
        raise ValueError("Yahoo chart response has no result")
    item = result[0]
    timestamps = item.get("timestamp")
    indicators = item.get("indicators")
    if not isinstance(timestamps, list) or not isinstance(indicators, dict):
        raise ValueError("Yahoo chart response missing timestamps/indicators")
    quotes = indicators.get("quote")
    if not isinstance(quotes, list) or not quotes:
        raise ValueError("Yahoo chart response missing quote block")
    quote_block = quotes[0]
    closes = quote_block.get("close")
    volumes = quote_block.get("volume")
    if not isinstance(closes, list):
        raise ValueError("Yahoo chart response missing close series")
    if volumes is None:
        volumes = [None] * len(closes)
    if not isinstance(volumes, list):
        raise ValueError("Yahoo chart response has invalid volume series")
    if len(timestamps) != len(closes):
        raise ValueError("Yahoo chart timestamp and close lengths differ")

    observations: list[Observation] = []
    for idx, raw_ts in enumerate(timestamps):
        raw_close = closes[idx]
        if raw_ts is None or raw_close is None:
            continue
        raw_volume = volumes[idx] if idx < len(volumes) else None
        observations.append(
            Observation(
                observed_date=datetime.fromtimestamp(int(raw_ts), tz=UTC).date(),
                close=float(raw_close),
                volume=int(raw_volume) if raw_volume is not None else None,
            )
        )
    if not observations:
        raise ValueError("Yahoo chart response contains no usable observations")
    observations.sort(key=lambda row: row.observed_date)
    return observations


def _previous_observation(observations: list[Observation], target: date) -> Observation:
    matches = [row for row in observations if row.observed_date <= target]
    if not matches:
        raise ValueError(f"No observation at or before {target.isoformat()}")
    return matches[-1]


def _return_pct(latest: Observation, prior: Observation) -> float:
    if prior.close == 0:
        raise ValueError("Cannot calculate return from zero close")
    return (latest.close / prior.close - 1.0) * 100.0


def summarize_observations(observations: list[Observation]) -> dict[str, Any]:
    if len(observations) < 2:
        raise ValueError("At least two observations are required")
    latest = observations[-1]
    five_sessions_prior = observations[-6] if len(observations) >= 6 else observations[0]
    one_month_prior = _previous_observation(observations, subtract_months(latest.observed_date, 1))
    three_month_prior = _previous_observation(observations, subtract_months(latest.observed_date, 3))
    return {
        "as_of": latest.observed_date.isoformat(),
        "close": latest.close,
        "volume": latest.volume,
        "return_5_sessions_pct": _return_pct(latest, five_sessions_prior),
        "return_1m_pct": _return_pct(latest, one_month_prior),
        "return_3m_pct": _return_pct(latest, three_month_prior),
        "anchors": {
            "five_sessions_prior": five_sessions_prior.observed_date.isoformat(),
            "one_month_prior": one_month_prior.observed_date.isoformat(),
            "three_month_prior": three_month_prior.observed_date.isoformat(),
        },
    }


def fetch_yahoo_chart(session: requests.Session, ticker: str, *, timeout: int) -> dict[str, Any]:
    ensure_yahoo_ticker(ticker)
    encoded = quote(ticker, safe="")
    period2 = int(datetime.now(tz=UTC).timestamp()) + 86400
    period1 = period2 - 220 * 86400
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}"
        f"?period1={period1}&period2={period2}&interval=1d&events=history"
    )
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    return {
        "ticker": ticker,
        "source_url": url,
        "summary": summarize_observations(parse_yahoo_chart(payload)),
    }


def html_to_text(raw_html: str) -> str:
    parser = TextExtractor()
    parser.feed(raw_html)
    return parser.text()


def signed_number(value: str) -> float | None:
    normalized = value.replace(",", "").replace("＋", "+").replace("▲", "-").replace("△", "-")
    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", normalized)
    return float(matches[-1]) if matches else None


def extract_metric_block(text: str, metric: str, unit: str) -> tuple[float | None, float | None]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    indexes = [index for index, line in enumerate(lines) if line == metric]
    if not indexes:
        return None, None
    window = lines[indexes[0] + 1 : indexes[0] + 18]
    latest: float | None = None
    average: float | None = None
    for line in window:
        if latest is None and re.search(r"\d{4}年.*期", line) and unit in line:
            latest = signed_number(line)
        if "期間平均" in line and unit in line:
            average = signed_number(line)
            break
    return latest, average


def extract_cagr(text: str, metric: str) -> float | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    indexes = [index for index, line in enumerate(lines) if line == metric]
    if not indexes:
        return None
    for line in lines[indexes[0] + 1 : indexes[0] + 18]:
        if "CAGR" in line:
            return signed_number(line)
    return None


def parse_shashi_text(text: str) -> dict[str, Any]:
    roe, roe_avg = extract_metric_block(text, "ROE", "%")
    per, per_avg = extract_metric_block(text, "PER", "倍")
    pbr, pbr_avg = extract_metric_block(text, "PBR", "倍")
    op_margin, op_margin_avg = extract_metric_block(text, "営業利益率", "%")
    net_margin, net_margin_avg = extract_metric_block(text, "当期純利益率", "%")
    return {
        "roe_pct": roe,
        "roe_period_avg_pct": roe_avg,
        "per_x": per,
        "per_period_avg_x": per_avg,
        "pbr_x": pbr,
        "pbr_period_avg_x": pbr_avg,
        "operating_margin_pct": op_margin,
        "operating_margin_period_avg_pct": op_margin_avg,
        "net_margin_pct": net_margin,
        "net_margin_period_avg_pct": net_margin_avg,
        "sales_cagr_pct": extract_cagr(text, "売上高"),
        "net_income_cagr_pct": extract_cagr(text, "当期純利益"),
    }


def fetch_shashi(session: requests.Session, code: str, *, timeout: int) -> dict[str, Any]:
    url = f"https://the-shashi.com/tse/{code}/current/"
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return {"source_url": url, "metrics": parse_shashi_text(html_to_text(response.text))}


def parse_kabutan_events(raw_html: str, code: str) -> list[dict[str, str]]:
    text = html_to_text(raw_html)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
    events: list[dict[str, str]] = []
    seen: set[str] = set()
    for line in lines:
        if code not in line and not any(keyword in line for keyword in DISCLOSURE_KEYWORDS):
            continue
        if not any(keyword in line for keyword in DISCLOSURE_KEYWORDS):
            continue
        normalized = line[:500]
        if normalized not in seen:
            seen.add(normalized)
            events.append({"headline": normalized})
        if len(events) >= 10:
            break
    return events


def fetch_kabutan(session: requests.Session, code: str, *, timeout: int) -> dict[str, Any]:
    url = f"https://kabutan.jp/stock/news?code={code}"
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return {"source_url": url, "events": parse_kabutan_events(response.text, code)}


def load_watchlist(path: Path) -> list[dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("watchlist must contain non-empty records")
    seen: set[str] = set()
    normalized: list[dict[str, str]] = []
    for record in records:
        ticker = ensure_yahoo_ticker(str(record["ticker"]))
        code = ticker.split(".")[0]
        if ticker in seen:
            raise ValueError(f"duplicate ticker: {ticker}")
        seen.add(ticker)
        normalized.append({"ticker": ticker, "code": code, "name": str(record["name"])})
    return normalized


def collect(
    *,
    watchlist_path: Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    web_delay_seconds: float = 0.7,
    include_shashi: bool = True,
    include_kabutan: bool = True,
) -> dict[str, Any]:
    retrieved_at = iso_now()
    watchlist = load_watchlist(watchlist_path)
    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json,text/html,*/*"})

    market: list[dict[str, Any]] = []
    fundamentals: list[dict[str, Any]] = []
    disclosures: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    source_urls: list[str] = []

    for record in watchlist:
        ticker = record["ticker"]
        try:
            result = fetch_yahoo_chart(session, ticker, timeout=timeout)
            source_urls.append(result["source_url"])
            market.append({**record, **result["summary"], "source_url": result["source_url"]})
        except Exception as exc:
            errors.append({"scope": ticker, "source": "yahoo_finance", "error": str(exc)})

    try:
        fx_result = fetch_yahoo_chart(session, "JPY=X", timeout=timeout)
        source_urls.append(fx_result["source_url"])
        fx = {"ticker": "JPY=X", **fx_result["summary"], "source_url": fx_result["source_url"]}
    except Exception as exc:
        fx = None
        errors.append({"scope": "JPY=X", "source": "yahoo_finance", "error": str(exc)})

    for record in watchlist:
        code = record["code"]
        if include_shashi:
            try:
                result = fetch_shashi(session, code, timeout=timeout)
                source_urls.append(result["source_url"])
                fundamentals.append({**record, **result["metrics"], "source_url": result["source_url"]})
            except Exception as exc:
                errors.append({"scope": code, "source": "the_shashi", "error": str(exc)})
            time.sleep(web_delay_seconds)
        if include_kabutan:
            try:
                result = fetch_kabutan(session, code, timeout=timeout)
                source_urls.append(result["source_url"])
                disclosures.append({**record, "events": result["events"], "source_url": result["source_url"]})
            except Exception as exc:
                errors.append({"scope": code, "source": "kabutan", "error": str(exc)})
            time.sleep(web_delay_seconds)

    expected_market = len(watchlist)
    status = "VERIFIED" if len(market) == expected_market and fx is not None else "PARTIAL"
    return {
        "schema_version": "investor2.japan-yen-equity-monitor.v1",
        "retrieved_at": retrieved_at,
        "status": status,
        "watchlist": watchlist,
        "market": market,
        "fx": fx,
        "fundamentals": fundamentals,
        "disclosures": disclosures,
        "errors": errors,
        "provenance": {
            "tool": "scripts/japan_equity_monitor.py",
            "operation": "Yahoo daily bars + The社史 current metrics + 株探 disclosure headlines",
            "query_or_scope": ",".join(record["ticker"] for record in watchlist),
            "retrieved_at": retrieved_at,
            "source_urls": sorted(set(source_urls)),
        },
    }


def default_output_path(retrieved_at: str) -> Path:
    stamp = retrieved_at.replace("-", "").replace(":", "")
    return DEFAULT_OUTPUT_DIR / f"japan_yen_equity_monitor_{stamp}.json"


def register_snapshot(artifact_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    from scripts.snapshot_store import append_entry, build_entry, load_registry

    relative = artifact_path.resolve().relative_to(ROOT.resolve()).as_posix()
    entry = build_entry(
        root=ROOT,
        registry=load_registry(),
        dataset_id="japan_yen_equity_monitor",
        reuse_key="market/japan/yen-beneficiary-watchlist",
        artifact_path=relative,
        source="public_web_research",
        source_kind="api",
        observed_at=str(payload["retrieved_at"]),
        schema_version=str(payload["schema_version"]),
        provenance=dict(payload["provenance"]),
    )
    append_entry(entry)
    return entry


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Collect a J-Quants-free Japan equity watch snapshot.")
    parser.add_argument("--watchlist", type=Path, default=DEFAULT_WATCHLIST)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--web-delay-seconds", type=float, default=0.7)
    parser.add_argument("--skip-shashi", action="store_true")
    parser.add_argument("--skip-kabutan", action="store_true")
    parser.add_argument("--register", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = collect(
        watchlist_path=args.watchlist,
        timeout=args.timeout,
        web_delay_seconds=args.web_delay_seconds,
        include_shashi=not args.skip_shashi,
        include_kabutan=not args.skip_kabutan,
    )
    output = args.output or default_output_path(str(payload["retrieved_at"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    response: dict[str, Any] = {
        "status": payload["status"],
        "artifact_path": output.resolve().relative_to(ROOT.resolve()).as_posix()
        if ROOT.resolve() in output.resolve().parents
        else str(output.resolve()),
        "errors": payload["errors"],
    }
    if args.register:
        if payload["status"] != "VERIFIED":
            print(json.dumps(response, ensure_ascii=False, sort_keys=True))
            print("Refusing to register PARTIAL market snapshot.", file=sys.stderr)
            return 2
        response["snapshot"] = register_snapshot(output, payload)
    print(json.dumps(response, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
