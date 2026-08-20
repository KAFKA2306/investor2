from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

from src.io.market_data_sources import GDELT_LAST_UPDATE_URL, parse_gdelt_gkg_zip, parse_gdelt_last_update, utc_now_iso


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "KAFKA2306/investor2 GDELT discovery collector"})
    with urlopen(req, timeout=90) as response:
        return response.read()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issuer-master", default="data/market/edinet_issuer_master.json")
    parser.add_argument("--output", default="data/market/gdelt_company_news_latest.json")
    args = parser.parse_args()
    master = json.loads(Path(args.issuer_master).read_text())
    latest = fetch(GDELT_LAST_UPDATE_URL).decode("utf-8")
    gkg_url = parse_gdelt_last_update(latest)
    result = parse_gdelt_gkg_zip(fetch(gkg_url), issuer_master=master, source_url=gkg_url, retrieved_at=utc_now_iso())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"source_url": gkg_url, "event_count": result["event_count"], "source_sha256": result["source_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
