from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import scripts.factset_insight_delivery as delivery
import scripts.factset_insight_monitor as monitor


ARTICLE_ID = "https://insight.factset.com/example-article"
ARTICLE_URL = ARTICLE_ID


def sample_article() -> dict[str, Any]:
    return {
        "article_id": ARTICLE_ID,
        "guid": ARTICLE_ID,
        "article_url": ARTICLE_URL,
        "title": "Example FactSet article",
        "author": "FactSet Insight",
        "published_at": "2026-08-28T17:12:57Z",
    }


def sample_feed() -> dict[str, Any]:
    return {
        "schema_version": monitor.SCHEMA_VERSION,
        "source": "FactSet Insight",
        "source_feed_url": monitor.FEED_URL,
        "feed_title": "FactSet Insight",
        "article_count": 1,
        "articles": [sample_article()],
    }


def write_inputs(root: Path, *, delivered: bool) -> tuple[Path, Path]:
    feed_path = root / "feed.json"
    state_path = root / "state.json"
    feed_path.write_text(json.dumps(sample_feed()), encoding="utf-8")
    monitor.write_state_atomic(
        state_path,
        {
            "schema_version": monitor.DELIVERY_STATE_SCHEMA,
            "delivered_article_ids": [ARTICLE_ID] if delivered else [],
        },
    )
    return feed_path, state_path


class FactSetInsightDeliveryTest(unittest.TestCase):
    def test_extract_article_text_prefers_article_and_skips_non_content(self) -> None:
        article_text = "FactSetの記事本文です。" * 80
        payload = (
            "<html><body><nav>navigation should disappear</nav><main>"
            f"<article>{article_text}<script>script should disappear</script></article>"
            "main fallback text"
            "</main></body></html>"
        ).encode()
        extracted = delivery.extract_article_text(payload)
        self.assertIn("FactSetの記事本文です。", extracted)
        self.assertNotIn("navigation should disappear", extracted)
        self.assertNotIn("script should disappear", extracted)
        self.assertNotIn("main fallback text", extracted)

    def test_extract_article_text_fails_closed_on_insufficient_content(self) -> None:
        with self.assertRaisesRegex(AssertionError, "insufficient text"):
            delivery.extract_article_text(b"<html><body><article>short</article></body></html>")

    def test_validate_summary_requires_three_to_five_japanese_sentences(self) -> None:
        sentences = delivery.validate_summary(
            {"summary_sentences": ["売上は増加した。", "利益率も改善した。", "一時要因が含まれる。"]}
        )
        self.assertEqual(len(sentences), 3)
        with self.assertRaisesRegex(AssertionError, "3 to 5"):
            delivery.validate_summary({"summary_sentences": ["短すぎる。"]})
        with self.assertRaisesRegex(AssertionError, "Japanese"):
            delivery.validate_summary(
                {"summary_sentences": ["Revenue increased.", "Margins improved.", "One-off gains mattered."]}
            )

    def test_render_comment_preserves_original_timestamp_and_jst(self) -> None:
        rendered = delivery.render_comment(
            sample_article(),
            ["売上は増加した。", "利益率も改善した。", "一時要因が含まれる。"],
        )
        self.assertIn("2026-08-29 02:12 JST", rendered)
        self.assertIn("2026-08-28T17:12:57Z", rendered)
        self.assertIn(ARTICLE_URL, rendered)
        self.assertIn(delivery.delivery_marker(ARTICLE_ID), rendered)

    def test_successful_delivery_acknowledges_only_after_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feed_path, state_path = write_inputs(Path(tmp), delivered=False)
            events: list[str] = []

            def fake_post_comment(**kwargs: Any) -> None:
                self.assertIn(ARTICLE_URL, str(kwargs["body"]))
                before = monitor.load_delivery_state(state_path)
                self.assertEqual(before["delivered_article_ids"], [])
                events.append("posted")

            with (
                patch.object(delivery, "comment_already_exists", return_value=False),
                patch.object(delivery, "download_article_html", return_value=b"article html"),
                patch.object(delivery, "extract_article_text", return_value="article body"),
                patch.object(
                    delivery,
                    "summarize_article",
                    return_value=["売上は増加した。", "利益率も改善した。", "一時要因が含まれる。"],
                ),
                patch.object(delivery, "post_comment", side_effect=fake_post_comment),
            ):
                metrics = delivery.deliver_pending(
                    feed_path=feed_path,
                    state_path=state_path,
                    repository="KAFKA2306/investor2",
                    issue_number=242,
                    github_token="test-token",
                    model="test-model",
                    ollama_url="http://127.0.0.1:11434",
                )

            self.assertEqual(events, ["posted"])
            self.assertEqual(metrics["delivered_count"], 1)
            after = monitor.load_delivery_state(state_path)
            self.assertEqual(after["delivered_article_ids"], [ARTICLE_ID])

    def test_delivery_failure_does_not_acknowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feed_path, state_path = write_inputs(Path(tmp), delivered=False)
            with (
                patch.object(delivery, "comment_already_exists", return_value=False),
                patch.object(delivery, "download_article_html", return_value=b"article html"),
                patch.object(delivery, "extract_article_text", return_value="article body"),
                patch.object(
                    delivery,
                    "summarize_article",
                    return_value=["売上は増加した。", "利益率も改善した。", "一時要因が含まれる。"],
                ),
                patch.object(delivery, "post_comment", side_effect=AssertionError("delivery failed")),
            ):
                with self.assertRaisesRegex(AssertionError, "delivery failed"):
                    delivery.deliver_pending(
                        feed_path=feed_path,
                        state_path=state_path,
                        repository="KAFKA2306/investor2",
                        issue_number=242,
                        github_token="test-token",
                        model="test-model",
                        ollama_url="http://127.0.0.1:11434",
                    )
            after = monitor.load_delivery_state(state_path)
            self.assertEqual(after["delivered_article_ids"], [])

    def test_existing_delivery_marker_recovers_without_duplicate_comment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feed_path, state_path = write_inputs(Path(tmp), delivered=False)
            with (
                patch.object(delivery, "comment_already_exists", return_value=True),
                patch.object(delivery, "download_article_html") as download,
                patch.object(delivery, "summarize_article") as summarize,
                patch.object(delivery, "post_comment") as post,
            ):
                metrics = delivery.deliver_pending(
                    feed_path=feed_path,
                    state_path=state_path,
                    repository="KAFKA2306/investor2",
                    issue_number=242,
                    github_token="test-token",
                    model="test-model",
                    ollama_url="http://127.0.0.1:11434",
                )
            download.assert_not_called()
            summarize.assert_not_called()
            post.assert_not_called()
            self.assertEqual(metrics["reused_delivery_count"], 1)
            self.assertEqual(monitor.load_delivery_state(state_path)["delivered_article_ids"], [ARTICLE_ID])

    def test_silent_path_does_not_call_delivery_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            feed_path, state_path = write_inputs(Path(tmp), delivered=True)
            with (
                patch.object(delivery, "comment_already_exists") as comments,
                patch.object(delivery, "download_article_html") as download,
                patch.object(delivery, "summarize_article") as summarize,
                patch.object(delivery, "post_comment") as post,
            ):
                metrics = delivery.deliver_pending(
                    feed_path=feed_path,
                    state_path=state_path,
                    repository="KAFKA2306/investor2",
                    issue_number=242,
                    github_token="test-token",
                    model="test-model",
                    ollama_url="http://127.0.0.1:11434",
                )
            comments.assert_not_called()
            download.assert_not_called()
            summarize.assert_not_called()
            post.assert_not_called()
            self.assertEqual(metrics["new_article_count"], 0)


if __name__ == "__main__":
    unittest.main()
