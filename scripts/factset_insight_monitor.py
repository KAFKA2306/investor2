#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from datetime import UTC
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "investor2.factset-insight-feed.v1"
DELIVERY_STATE_SCHEMA = "investor2.factset-insight-delivery-state.v1"
FEED_URL = "https://insight.factset.com/rss.xml"


def _text(element: ET.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    value = element.text.strip()
    return value or None


def _child_by_local_name(parent: ET.Element, *names: str) -> ET.Element | None:
    expected = set(names)
    for child in parent:
        local = child.tag.rsplit("}", 1)[-1]
        if local in expected:
            return child
    return None


def _parse_published_at(value: str) -> str:
    parsed = parsedate_to_datetime(value)
    if parsed is None or parsed.tzinfo is None:
        raise AssertionError(f"FactSet RSS pubDate must include timezone: {value!r}")
    return parsed.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _validate_feed(feed: dict[str, Any]) -> dict[str, Any]:
    if feed.get("schema_version") != SCHEMA_VERSION:
        raise AssertionError("FactSet feed snapshot schema mismatch")
    if feed.get("source_feed_url") != FEED_URL:
        raise AssertionError("FactSet feed snapshot source URL mismatch")
    articles = feed.get("articles")
    if not isinstance(articles, list) or not articles:
        raise AssertionError("FactSet feed snapshot contains no articles")
    identities: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for article in articles:
        if not isinstance(article, dict):
            raise AssertionError("FactSet feed snapshot article must be an object")
        missing = [field for field in ("article_id", "article_url", "title", "published_at") if not article.get(field)]
        if missing:
            raise AssertionError(f"FactSet feed snapshot article missing required fields {missing}")
        identity = str(article["article_id"])
        if identity in identities:
            raise AssertionError(f"FactSet feed snapshot contains duplicate article identity: {identity!r}")
        identities.add(identity)
        normalized.append(
            {
                "article_id": identity,
                "guid": article.get("guid"),
                "article_url": str(article["article_url"]),
                "title": str(article["title"]),
                "author": article.get("author"),
                "published_at": str(article["published_at"]),
            }
        )
    normalized.sort(key=lambda article: (article["published_at"], article["article_id"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "FactSet Insight",
        "source_feed_url": FEED_URL,
        "feed_title": str(feed.get("feed_title") or "FactSet Insight"),
        "article_count": len(normalized),
        "articles": normalized,
    }


def parse_rss(payload: bytes, *, source_feed_url: str = FEED_URL) -> dict[str, Any]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise AssertionError(f"FactSet RSS is malformed XML: {exc}") from exc

    if root.tag.rsplit("}", 1)[-1].lower() != "rss":
        raise AssertionError(f"FactSet feed root must be rss, got {root.tag!r}")
    channel = _child_by_local_name(root, "channel")
    if channel is None:
        raise AssertionError("FactSet RSS is missing channel")

    feed_title = _text(_child_by_local_name(channel, "title"))
    if not feed_title:
        raise AssertionError("FactSet RSS channel is missing title")

    articles: list[dict[str, Any]] = []
    identities: set[str] = set()
    items = [child for child in channel if child.tag.rsplit("}", 1)[-1] == "item"]
    if not items:
        raise AssertionError("FactSet RSS contains no items")

    for item in items:
        title = _text(_child_by_local_name(item, "title"))
        article_url = _text(_child_by_local_name(item, "link"))
        guid = _text(_child_by_local_name(item, "guid"))
        author = _text(_child_by_local_name(item, "creator", "author"))
        pub_date = _text(_child_by_local_name(item, "pubDate", "published"))

        missing = [
            field
            for field, value in (("title", title), ("article_url", article_url), ("published_at", pub_date))
            if not value
        ]
        if missing:
            raise AssertionError(f"FactSet RSS item missing required fields {missing}")
        if not article_url.startswith(("https://", "http://")):
            raise AssertionError(f"FactSet RSS item has invalid article URL: {article_url!r}")

        identity = guid or article_url
        if identity in identities:
            raise AssertionError(f"FactSet RSS contains duplicate article identity: {identity!r}")
        identities.add(identity)

        articles.append(
            {
                "article_id": identity,
                "guid": guid,
                "article_url": article_url,
                "title": title,
                "author": author,
                "published_at": _parse_published_at(pub_date),
            }
        )

    articles.sort(key=lambda article: (article["published_at"], article["article_id"]))
    return {
        "schema_version": SCHEMA_VERSION,
        "source": "FactSet Insight",
        "source_feed_url": source_feed_url,
        "feed_title": feed_title,
        "article_count": len(articles),
        "articles": articles,
    }


def load_feed(*, rss: Path | None = None, feed_json: Path | None = None) -> dict[str, Any]:
    if (rss is None) == (feed_json is None):
        raise AssertionError("provide exactly one of RSS XML or accepted feed JSON")
    if rss is not None:
        return parse_rss(rss.read_bytes())
    assert feed_json is not None
    return _validate_feed(json.loads(feed_json.read_text(encoding="utf-8")))


def load_delivery_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise AssertionError(f"FactSet delivery state does not exist; bootstrap first: {path}")
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != DELIVERY_STATE_SCHEMA:
        raise AssertionError("FactSet delivery state schema mismatch")
    delivered = state.get("delivered_article_ids")
    if not isinstance(delivered, list) or any(not isinstance(value, str) or not value for value in delivered):
        raise AssertionError("FactSet delivery state must contain non-empty string article IDs")
    if len(delivered) != len(set(delivered)):
        raise AssertionError("FactSet delivery state contains duplicate article IDs")
    return {"schema_version": DELIVERY_STATE_SCHEMA, "delivered_article_ids": sorted(delivered)}


def pending_articles(feed: dict[str, Any], state: dict[str, Any]) -> list[dict[str, Any]]:
    delivered = set(state["delivered_article_ids"])
    pending = [article for article in feed["articles"] if article["article_id"] not in delivered]
    pending.sort(key=lambda article: (article["published_at"], article["article_id"]))
    return pending


def render_monitor_output(articles: list[dict[str, Any]]) -> str:
    if not articles:
        return "[SILENT]\n"
    return "\n".join(
        "NEW_ARTICLE\t" + json.dumps(article, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for article in articles
    ) + "\n"


def bootstrap_state(feed: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": DELIVERY_STATE_SCHEMA,
        "delivered_article_ids": sorted(article["article_id"] for article in feed["articles"]),
    }


def acknowledge_articles(state: dict[str, Any], article_ids: list[str]) -> dict[str, Any]:
    if not article_ids or any(not article_id for article_id in article_ids):
        raise AssertionError("ack requires at least one non-empty article ID")
    delivered = set(state["delivered_article_ids"])
    delivered.update(article_ids)
    return {"schema_version": DELIVERY_STATE_SCHEMA, "delivered_article_ids": sorted(delivered)}


def write_state_atomic(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def materialize_snapshot(payload: dict[str, Any], output_dir: Path, latest_path: Path | None) -> Path:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    latest_published_at = max(article["published_at"] for article in payload["articles"])
    latest_date = latest_published_at[:10]
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / f"factset_insight_feed_{latest_date}_{digest[:12]}.json"
    artifact.write_text(serialized, encoding="utf-8")
    if latest_path is not None:
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        latest_path.write_text(serialized, encoding="utf-8")
    return artifact


def _add_feed_input(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--rss", type=Path)
    group.add_argument("--feed-json", type=Path)


def _print_path(path: Path) -> None:
    resolved = path.resolve()
    root = Path.cwd().resolve()
    print(resolved.relative_to(root).as_posix() if resolved.is_relative_to(root) else path.as_posix())


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministically monitor and materialize FactSet Insight RSS metadata.")
    sub = parser.add_subparsers(dest="command", required=True)

    bootstrap = sub.add_parser("bootstrap", help="Mark the current feed as the initial delivered baseline.")
    _add_feed_input(bootstrap)
    bootstrap.add_argument("--state", type=Path, required=True)

    monitor = sub.add_parser("monitor", help="Emit only undelivered article metadata; never mutates state.")
    _add_feed_input(monitor)
    monitor.add_argument("--state", type=Path, required=True)

    ack = sub.add_parser("ack", help="Acknowledge article IDs only after downstream delivery succeeds.")
    ack.add_argument("--state", type=Path, required=True)
    ack.add_argument("--article-id", action="append", dest="article_ids", required=True)

    snapshot = sub.add_parser("snapshot", help="Materialize RSS metadata as a content-addressed JSON snapshot.")
    snapshot.add_argument("--rss", type=Path, required=True)
    snapshot.add_argument("--output-dir", type=Path, required=True)
    snapshot.add_argument("--latest-path", type=Path)

    args = parser.parse_args()

    if args.command == "bootstrap":
        if args.state.exists():
            raise AssertionError(f"refusing to overwrite existing FactSet delivery state: {args.state}")
        feed = load_feed(rss=args.rss, feed_json=args.feed_json)
        write_state_atomic(args.state, bootstrap_state(feed))
        print("[SILENT]")
        return

    if args.command == "monitor":
        feed = load_feed(rss=args.rss, feed_json=args.feed_json)
        state = load_delivery_state(args.state)
        sys.stdout.write(render_monitor_output(pending_articles(feed, state)))
        return

    if args.command == "ack":
        state = load_delivery_state(args.state)
        write_state_atomic(args.state, acknowledge_articles(state, args.article_ids))
        return

    payload = parse_rss(args.rss.read_bytes())
    _print_path(materialize_snapshot(payload, args.output_dir, args.latest_path))


if __name__ == "__main__":
    main()
