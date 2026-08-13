#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "fetch_arxiv_finance_metadata.py"
sys.path.insert(0, str(MODULE_PATH.parent))
spec = importlib.util.spec_from_file_location("fetch_arxiv_finance_metadata", MODULE_PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

SAMPLE_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <opensearch:totalResults>1</opensearch:totalResults>
  <entry>
    <id>http://arxiv.org/abs/2112.04755v2</id>
    <updated>2022-01-03T12:00:00Z</updated>
    <published>2021-12-09T11:00:00Z</published>
    <title>
      High-Dimensional Stock Portfolio Trading with Deep Reinforcement Learning
    </title>
    <summary>  A sample   abstract. </summary>
    <author><name>Uta Pigorsch</name></author>
    <author><name>Sebastian Schaefer</name></author>
    <category term="q-fin.PM" scheme="http://arxiv.org/schemas/atom"/>
    <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
    <arxiv:primary_category term="q-fin.PM"/>
    <arxiv:doi>10.0000/example</arxiv:doi>
    <link href="http://arxiv.org/abs/2112.04755v2" rel="alternate" type="text/html"/>
    <link title="pdf" href="http://arxiv.org/pdf/2112.04755v2" rel="related" type="application/pdf"/>
  </entry>
</feed>
"""


def test_query_scope() -> None:
    query = module.build_search_query(2021)
    assert "cat:q-fin.PM" in query
    assert "cat:q-fin.TR" in query
    assert "cat:q-fin.EC" not in query
    assert "submittedDate:[202101010000 TO 202112312359]" in query


def test_parse_feed() -> None:
    total, records = module.parse_feed(SAMPLE_XML)
    assert total == 1
    record = records[0]
    assert record["arxiv_id"] == "2112.04755"
    assert record["versioned_id"] == "2112.04755v2"
    assert record["title"] == (
        "High-Dimensional Stock Portfolio Trading with Deep Reinforcement Learning"
    )
    assert record["authors"] == ["Uta Pigorsch", "Sebastian Schaefer"]
    assert record["abstract"] == "A sample abstract."
    assert record["primary_category"] == "q-fin.PM"
    assert record["categories"] == ["cs.LG", "q-fin.PM"]
    assert record["doi"] == "10.0000/example"
    assert record["abs_url"].startswith("https://arxiv.org/abs/")
    assert record["pdf_url"].startswith("https://arxiv.org/pdf/")


if __name__ == "__main__":
    test_query_scope()
    test_parse_feed()
    print("PASS")
