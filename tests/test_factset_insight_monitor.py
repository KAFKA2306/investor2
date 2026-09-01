from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import factset_insight_monitor as monitor


RSS = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>FactSet Insight</title>
    <item>
      <title>Newer article</title>
      <link>https://insight.factset.com/newer</link>
      <guid>factset-newer</guid>
      <dc:creator>Analyst B</dc:creator>
      <pubDate>Sat, 29 Aug 2026 02:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Older article</title>
      <link>https://insight.factset.com/older</link>
      <guid>factset-older</guid>
      <dc:creator>Analyst A</dc:creator>
      <pubDate>Fri, 28 Aug 2026 17:12:57 GMT</pubDate>
    </item>
  </channel>
</rss>
'''
RSS_REVERSED = b'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>FactSet Insight</title>
    <item>
      <title>Older article</title>
      <link>https://insight.factset.com/older</link>
      <guid>factset-older</guid>
      <dc:creator>Analyst A</dc:creator>
      <pubDate>Fri, 28 Aug 2026 17:12:57 GMT</pubDate>
    </item>
    <item>
      <title>Newer article</title>
      <link>https://insight.factset.com/newer</link>
      <guid>factset-newer</guid>
      <dc:creator>Analyst B</dc:creator>
      <pubDate>Sat, 29 Aug 2026 02:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
'''


class FactSetInsightMonitorTest(unittest.TestCase):
    def test_parse_rss_normalizes_and_sorts_articles(self) -> None:
        feed = monitor.parse_rss(RSS)
        self.assertEqual(feed["schema_version"], monitor.SCHEMA_VERSION)
        self.assertEqual(feed["article_count"], 2)
        self.assertEqual([a["article_id"] for a in feed["articles"]], ["factset-older", "factset-newer"])
        self.assertEqual(feed["articles"][0]["published_at"], "2026-08-28T17:12:57Z")
        self.assertEqual(feed["articles"][0]["author"], "Analyst A")

    def test_item_order_does_not_change_monitor_output(self) -> None:
        state = {"schema_version": monitor.DELIVERY_STATE_SCHEMA, "delivered_article_ids": []}
        normal = monitor.render_monitor_output(monitor.pending_articles(monitor.parse_rss(RSS), state))
        reversed_output = monitor.render_monitor_output(monitor.pending_articles(monitor.parse_rss(RSS_REVERSED), state))
        self.assertEqual(normal, reversed_output)

    def test_bootstrap_is_silent_and_marks_current_feed_delivered(self) -> None:
        feed = monitor.parse_rss(RSS)
        state = monitor.bootstrap_state(feed)
        self.assertEqual(state["delivered_article_ids"], ["factset-newer", "factset-older"])
        self.assertEqual(monitor.render_monitor_output(monitor.pending_articles(feed, state)), "[SILENT]\n")

    def test_one_undelivered_article_emits_exactly_one_new_article(self) -> None:
        feed = monitor.parse_rss(RSS)
        state = {"schema_version": monitor.DELIVERY_STATE_SCHEMA, "delivered_article_ids": ["factset-older"]}
        pending = monitor.pending_articles(feed, state)
        self.assertEqual([a["article_id"] for a in pending], ["factset-newer"])
        rendered = monitor.render_monitor_output(pending)
        self.assertEqual(rendered.count("NEW_ARTICLE\t"), 1)
        self.assertIn('"article_id":"factset-newer"', rendered)

    def test_ack_is_separate_from_monitor_and_makes_next_monitor_silent(self) -> None:
        feed = monitor.parse_rss(RSS)
        before = {"schema_version": monitor.DELIVERY_STATE_SCHEMA, "delivered_article_ids": ["factset-older"]}
        after = monitor.acknowledge_articles(before, ["factset-newer"])
        self.assertEqual(monitor.render_monitor_output(monitor.pending_articles(feed, after)), "[SILENT]\n")

    def test_missing_state_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.json"
            with self.assertRaisesRegex(AssertionError, "bootstrap first"):
                monitor.load_delivery_state(missing)

    def test_feed_json_is_a_valid_monitor_input(self) -> None:
        feed = monitor.parse_rss(RSS)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "feed.json"
            path.write_text(json.dumps(feed, ensure_ascii=False), encoding="utf-8")
            loaded = monitor.load_feed(feed_json=path)
            self.assertEqual(loaded, feed)

    def test_missing_required_item_field_fails_closed(self) -> None:
        broken = RSS.replace(b"<link>https://insight.factset.com/newer</link>", b"")
        with self.assertRaisesRegex(AssertionError, "missing required fields"):
            monitor.parse_rss(broken)

    def test_malformed_xml_fails_closed(self) -> None:
        with self.assertRaisesRegex(AssertionError, "malformed XML"):
            monitor.parse_rss(b"<rss><channel>")

    def test_materialized_snapshot_is_content_addressed(self) -> None:
        payload = monitor.parse_rss(RSS)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            latest = root / "latest.json"
            artifact = monitor.materialize_snapshot(payload, root / "snapshots", latest)
            serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
            digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]
            self.assertEqual(artifact.name, f"factset_insight_feed_2026-08-29_{digest}.json")
            self.assertEqual(latest.read_text(encoding="utf-8"), serialized)


if __name__ == "__main__":
    unittest.main()
