from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.io.market_data_sources import query_gdelt_events


def main() -> int:
    parser = argparse.ArgumentParser(description="Query normalized GDELT discovery snapshots")
    parser.add_argument("paths", nargs="+", help="JSON snapshots produced by ingest_gdelt_news.py")
    parser.add_argument("--security-code")
    parser.add_argument("--industry")
    parser.add_argument("--from", dest="observed_from")
    parser.add_argument("--to", dest="observed_to")
    args = parser.parse_args()
    datasets = [json.loads(Path(path).read_text()) for path in args.paths]
    rows = query_gdelt_events(
        datasets,
        security_code=args.security_code,
        industry=args.industry,
        observed_from=args.observed_from,
        observed_to=args.observed_to,
    )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
