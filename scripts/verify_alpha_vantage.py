from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from src.io.market_data_sources import ALPHA_VANTAGE_ENDPOINT, parse_alpha_vantage_daily, utc_now_iso


def fetch_json(params: dict[str, str]) -> dict[str, object]:
    url = f"{ALPHA_VANTAGE_ENDPOINT}?{urlencode(params)}"
    req = Request(url, headers={"User-Agent": "KAFKA2306/investor2 Alpha Vantage verification"})
    with urlopen(req, timeout=60) as response:
        return json.loads(response.read())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issuer-master", default="data/market/edinet_issuer_master.json")
    parser.add_argument("--output", default="data/market/alpha_vantage_verification.json")
    parser.add_argument("--sample-size", type=int, default=33)
    parser.add_argument(
        "--qualification-status",
        choices=("verified", "not_verified", "unresolved"),
        default="unresolved",
    )
    parser.add_argument("--qualification-evidence-url")
    parser.add_argument(
        "--symbol-template",
        required=True,
        help="Provider-verified symbol template containing {security_code}. No exchange suffix is assumed.",
    )
    args = parser.parse_args()
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        raise SystemExit("ALPHA_VANTAGE_API_KEY is required for live verification")
    if "{security_code}" not in args.symbol_template:
        raise SystemExit("--symbol-template must contain {security_code}; do not guess provider symbols")

    master = json.loads(Path(args.issuer_master).read_text())
    by_industry: dict[str, dict[str, object]] = {}
    for issuer in master["issuers"]:
        by_industry.setdefault(str(issuer["industry"]), issuer)
    sample = list(by_industry.values())[: args.sample_size]
    results = []
    for issuer in sample:
        code = str(issuer["security_code"])
        symbol = args.symbol_template.format(security_code=code)
        payload = fetch_json(
            {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": api_key,
            }
        )
        results.append(parse_alpha_vantage_daily(payload, security_code=code, symbol=symbol).__dict__)
        time.sleep(1.0)

    supported = sum(row["status"] == "supported" for row in results)
    statuses = {
        status: sum(row["status"] == status for row in results)
        for status in sorted({str(row["status"]) for row in results})
    }
    decision = "unresolved"
    if args.qualification_status == "verified" and supported == len(results) and results:
        decision = "adopt-candidate"
    elif args.qualification_status == "not_verified":
        decision = "standard-free-tier-only"
    report = {
        "schema_version": "investor2.alpha-vantage-verification.v1",
        "verified_at": utc_now_iso(),
        "qualification_status": args.qualification_status,
        "symbol_template": args.symbol_template,
        "qualification_evidence_url": args.qualification_evidence_url,
        "sample_count": len(results),
        "supported_count": supported,
        "coverage_ratio": (supported / len(results)) if results else 0.0,
        "statuses": statuses,
        "decision": decision,
        "results": results,
        "raw_responses_published": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "sample_count",
                    "supported_count",
                    "coverage_ratio",
                    "qualification_status",
                    "decision",
                )
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
