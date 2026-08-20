from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

from src.io.market_data_sources import (
    EDINET_CODELIST_URL,
    diff_issuer_masters,
    parse_edinet_code_zip,
    utc_now_iso,
)


def fetch(url: str) -> bytes:
    req = Request(
        url,
        headers={"User-Agent": "KAFKA2306/investor2 EDINET issuer master"},
    )
    with urlopen(req, timeout=60) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=EDINET_CODELIST_URL)
    parser.add_argument("--output", default="data/market/edinet_issuer_master.json")
    parser.add_argument(
        "--diff-output", default="data/market/edinet_issuer_master_diff.json"
    )
    args = parser.parse_args()
    output = Path(args.output)
    previous = json.loads(output.read_text()) if output.exists() else None
    master = parse_edinet_code_zip(
        fetch(args.url), source_url=args.url, retrieved_at=utc_now_iso()
    )
    diff = diff_issuer_masters(previous, master)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(master, ensure_ascii=False, indent=2) + "\n")
    Path(args.diff_output).write_text(
        json.dumps(diff, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "issuer_count": master["issuer_count"],
                "source_sha256": master["source_sha256"],
                "change_count": diff["change_count"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
