#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, override
from zoneinfo import ZoneInfo

from scripts.factset_insight_monitor import (
    acknowledge_articles,
    load_delivery_state,
    load_feed,
    pending_articles,
    write_state_atomic,
)

DELIVERY_SCHEMA = "investor2.factset-insight-delivery.v1"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:1.7b"
MAX_ARTICLE_BYTES = 2_000_000
MAX_BODY_CHARS = 24_000
MIN_BODY_CHARS = 500
JST = ZoneInfo("Asia/Tokyo")


class ArticleTextParser(HTMLParser):
    _SKIP_TAGS = {"script", "style", "svg", "nav", "footer", "form", "noscript", "header"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._article_depth = 0
        self._main_depth = 0
        self._article_parts: list[str] = []
        self._main_parts: list[str] = []
        self._body_parts: list[str] = []

    @override
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.lower()
        if normalized in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if normalized == "article":
            self._article_depth += 1
        elif normalized == "main":
            self._main_depth += 1

    @override
    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in self._SKIP_TAGS:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if normalized == "article" and self._article_depth:
            self._article_depth -= 1
        elif normalized == "main" and self._main_depth:
            self._main_depth -= 1

    @override
    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if not text:
            return
        self._body_parts.append(text)
        if self._article_depth:
            self._article_parts.append(text)
        if self._main_depth:
            self._main_parts.append(text)

    def text(self) -> str:
        for parts in (self._article_parts, self._main_parts, self._body_parts):
            value = "\n".join(parts).strip()
            if len(value) >= MIN_BODY_CHARS:
                return value[:MAX_BODY_CHARS]
        raise AssertionError("FactSet article extraction produced insufficient text")


def extract_article_text(payload: bytes) -> str:
    parser = ArticleTextParser()
    parser.feed(payload.decode("utf-8", errors="replace"))
    parser.close()
    return parser.text()


def download_article_html(url: str, *, timeout_seconds: int = 60) -> bytes:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "insight.factset.com":
        raise AssertionError(f"refusing non-FactSet article URL: {url!r}")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "KAFKA2306/investor2 FactSet Insight delivery",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        final_url = urllib.parse.urlparse(response.geturl())
        if final_url.scheme != "https" or final_url.hostname != "insight.factset.com":
            raise AssertionError(f"FactSet article redirected off publisher domain: {response.geturl()!r}")
        content_type = response.headers.get_content_type()
        if content_type not in {"text/html", "application/xhtml+xml"}:
            raise AssertionError(f"FactSet article returned unexpected content type: {content_type!r}")
        payload = response.read(MAX_ARTICLE_BYTES + 1)
    if len(payload) > MAX_ARTICLE_BYTES:
        raise AssertionError("FactSet article exceeded maximum accepted HTML size")
    return payload


def _summary_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "summary_sentences": {
                "type": "array",
                "minItems": 3,
                "maxItems": 5,
                "items": {"type": "string"},
            }
        },
        "required": ["summary_sentences"],
        "additionalProperties": False,
    }


def validate_summary(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        raise AssertionError("LLM summary must be a JSON object")
    sentences = payload.get("summary_sentences")
    if not isinstance(sentences, list) or not 3 <= len(sentences) <= 5:
        raise AssertionError("LLM summary must contain 3 to 5 sentences")
    normalized: list[str] = []
    for sentence in sentences:
        if not isinstance(sentence, str) or not sentence.strip():
            raise AssertionError("LLM summary sentence must be a non-empty string")
        text = " ".join(sentence.split())
        if not re.search(r"[ぁ-んァ-ヶ一-龯]", text):
            raise AssertionError("LLM summary sentence must be Japanese")
        normalized.append(text)
    return normalized


def summarize_article(
    *,
    title: str,
    body: str,
    model: str,
    ollama_url: str,
    timeout_seconds: int = 900,
) -> list[str]:
    schema = _summary_schema()
    prompt = (
        "以下はFactSet Insightの記事本文です。投資判断向けに日本語3〜5文で要約してください。"
        "本文に明示される数値、比較条件、一時要因、会計上の特殊要因を優先してください。"
        "本文にない数値・因果・推奨を作らず、投資助言にしないでください。"
        "JSON Schemaに厳密に従ってください。\n\n"
        f"タイトル: {title}\n\n本文:\n{body}"
    )
    request_payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You summarize publisher-authored financial research faithfully in Japanese.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "format": schema,
        "options": {"temperature": 0, "num_predict": 384},
    }
    request = urllib.request.Request(
        f"{ollama_url.rstrip('/')}/api/chat",
        data=json.dumps(request_payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_payload = json.loads(response.read().decode("utf-8"))
    message = response_payload.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise AssertionError("Ollama response did not contain message.content")
    return validate_summary(json.loads(message["content"]))


def delivery_marker(article_id: str) -> str:
    digest = hashlib.sha256(article_id.encode("utf-8")).hexdigest()[:20]
    return f"<!-- factset-insight-delivery:{digest} -->"


def _github_request(
    *,
    url: str,
    token: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 60,
) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "KAFKA2306/investor2 FactSet Insight delivery",
            **({"Content-Type": "application/json"} if payload is not None else {}),
        },
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def comment_already_exists(*, repository: str, issue_number: int, marker: str, token: str) -> bool:
    page = 1
    while True:
        rows = _github_request(
            url=f"https://api.github.com/repos/{repository}/issues/{issue_number}/comments?per_page=100&page={page}",
            token=token,
        )
        if not isinstance(rows, list):
            raise AssertionError("GitHub issue comments response must be a list")
        if any(isinstance(row, dict) and marker in str(row.get("body") or "") for row in rows):
            return True
        if len(rows) < 100:
            return False
        page += 1


def published_at_jst(published_at: str) -> str:
    normalized = published_at[:-1] + "+00:00" if published_at.endswith("Z") else published_at
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise AssertionError("published_at must include timezone")
    return parsed.astimezone(JST).strftime("%Y-%m-%d %H:%M JST")


def render_comment(article: dict[str, Any], summary_sentences: list[str]) -> str:
    marker = delivery_marker(str(article["article_id"]))
    bullets = "\n".join(f"- {sentence}" for sentence in summary_sentences)
    title = " ".join(str(article["title"]).split())
    return (
        f"{marker}\n"
        "### FactSet Insight 新着\n\n"
        f"**{title}**\n\n"
        f"公開: {published_at_jst(str(article['published_at']))} "
        f"(`{article['published_at']}`)\n\n"
        f"{bullets}\n\n"
        f"原文: {article['article_url']}\n\n"
        "_日本語要約はローカルLLMによる派生情報です。数値・主張は原文を正本として確認してください。_"
    )


def post_comment(*, repository: str, issue_number: int, body: str, token: str) -> None:
    response = _github_request(
        url=f"https://api.github.com/repos/{repository}/issues/{issue_number}/comments",
        token=token,
        method="POST",
        payload={"body": body},
    )
    if not isinstance(response, dict) or not response.get("id"):
        raise AssertionError("GitHub issue comment delivery did not return a comment id")


def _emit_failure_metrics(metrics: dict[str, Any], started: float) -> None:
    metrics["runtime_seconds"] = round(time.monotonic() - started, 3)
    print(json.dumps(metrics, ensure_ascii=False, sort_keys=True), file=sys.stderr)


def deliver_pending(
    *,
    feed_path: Path,
    state_path: Path,
    repository: str,
    issue_number: int,
    github_token: str,
    model: str,
    ollama_url: str,
) -> dict[str, Any]:
    started = time.monotonic()
    metrics: dict[str, Any] = {
        "schema_version": DELIVERY_SCHEMA,
        "fetch_failure": 0,
        "parse_failure": 0,
        "new_article_count": 0,
        "article_extract_failure": 0,
        "summarization_failure": 0,
        "delivery_failure": 0,
        "delivered_count": 0,
        "reused_delivery_count": 0,
    }

    try:
        feed = load_feed(feed_json=feed_path)
        state = load_delivery_state(state_path)
        pending = pending_articles(feed, state)
    except (AssertionError, OSError, json.JSONDecodeError):
        metrics["parse_failure"] += 1
        _emit_failure_metrics(metrics, started)
        raise

    metrics["new_article_count"] = len(pending)
    if not pending:
        metrics["runtime_seconds"] = round(time.monotonic() - started, 3)
        return metrics

    for article in pending:
        article_id = str(article["article_id"])
        marker = delivery_marker(article_id)
        try:
            if comment_already_exists(
                repository=repository,
                issue_number=issue_number,
                marker=marker,
                token=github_token,
            ):
                state = acknowledge_articles(state, [article_id])
                write_state_atomic(state_path, state)
                metrics["reused_delivery_count"] += 1
                continue
        except (AssertionError, OSError, urllib.error.URLError, json.JSONDecodeError):
            metrics["delivery_failure"] += 1
            _emit_failure_metrics(metrics, started)
            raise

        try:
            article_html = download_article_html(str(article["article_url"]))
        except (AssertionError, OSError, urllib.error.URLError):
            metrics["fetch_failure"] += 1
            _emit_failure_metrics(metrics, started)
            raise

        try:
            body = extract_article_text(article_html)
        except (AssertionError, OSError):
            metrics["article_extract_failure"] += 1
            _emit_failure_metrics(metrics, started)
            raise

        try:
            summary = summarize_article(
                title=str(article["title"]),
                body=body,
                model=model,
                ollama_url=ollama_url,
            )
        except (AssertionError, OSError, urllib.error.URLError, json.JSONDecodeError):
            metrics["summarization_failure"] += 1
            _emit_failure_metrics(metrics, started)
            raise

        try:
            post_comment(
                repository=repository,
                issue_number=issue_number,
                body=render_comment(article, summary),
                token=github_token,
            )
        except (AssertionError, OSError, urllib.error.URLError, json.JSONDecodeError):
            metrics["delivery_failure"] += 1
            _emit_failure_metrics(metrics, started)
            raise

        state = acknowledge_articles(state, [article_id])
        write_state_atomic(state_path, state)
        metrics["delivered_count"] += 1

    metrics["runtime_seconds"] = round(time.monotonic() - started, 3)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deliver pending FactSet Insight articles after successful local summarization."
    )
    parser.add_argument("--feed-json", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--issue-number", type=int, default=242)
    parser.add_argument("--github-token", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    args = parser.parse_args()
    metrics = deliver_pending(
        feed_path=args.feed_json,
        state_path=args.state,
        repository=args.repository,
        issue_number=args.issue_number,
        github_token=args.github_token,
        model=args.model,
        ollama_url=args.ollama_url,
    )
    print(json.dumps(metrics, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
