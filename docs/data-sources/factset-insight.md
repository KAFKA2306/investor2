# FactSet Insight RSS

## Purpose

FactSet Insight のpublisher-authored researchを、定常時にLLMを起動せず、新着記事だけを投資判断用の日本語要約へ送る。

RSS metadataは外部証拠の発見・記事identity・公開時刻の正本として扱う。記事本文と要約は別レイヤーであり、RSS metadataと混同しない。

## Source

- Feed: `https://insight.factset.com/rss.xml`
- Registered source: `factset_insight_rss`
- Feed snapshot schema: `investor2.factset-insight-feed.v1`
- Reuse key: `factset/insight/rss`
- Accepted feed snapshot: `data/factset_insight/latest_feed.json`
- Immutable snapshots: `data/snapshots/factset_insight/`
- Operational delivery cursor: `data/factset_insight/delivery_state.json`

RSSから保存する項目は以下のみ。

- `article_id` — RSS guid。guidがない場合のみarticle URLをidentityに使う。
- `guid`
- `article_url`
- `title`
- `author`
- `published_at` — timezone-aware RSS publication timestampをUTCへ正規化。

本文全文はpublic Git historyへ保存しない。

## Ownership boundaries

### GitHub / canonical source layer

`.github/workflows/factset-insight.yml` が毎日 `00:00 UTC`（`09:00 JST`）にpublisher RSSを取得する。

```text
RSS fetch
  -> strict XML parse
  -> normalized metadata JSON
  -> content-addressed snapshot
  -> snapshot_store register
  -> audit
  -> changed source content only commit
```

feed内容が前回accepted snapshotと同一なら、新しいcatalog rowを作らない。

### Delivery runtime

`factset_insight_monitor.py` のdelivery stateは、RSS evidence ledgerとは別の**operational cursor**である。記事を「観測した」ことと「通知に成功した」ことを混同しないために分離する。

GitHub-hosted runnerはephemeralなので、cursorだけを `data/factset_insight/delivery_state.json` として追跡する。このファイルはevidence snapshotではなく、再送制御のための運用状態である。

通常monitor:

```bash
python scripts/factset_insight_monitor.py monitor \
  --feed-json data/factset_insight/latest_feed.json \
  --state data/factset_insight/delivery_state.json
```

新着なし:

```text
[SILENT]
```

新着あり:

```text
NEW_ARTICLE\t{"article_id":"...","article_url":"...","author":"...","guid":"...","published_at":"...","title":"..."}
```

`[SILENT]` の場合、Ollamaのinstall/pull・記事本文取得・LLM推論は実行しない。

`NEW_ARTICLE` がある時だけ、workflowはrepo内で既に検証済みのlocal-only Ollama (`qwen3:1.7b`) を起動し、`scripts/factset_insight_delivery.py` を実行する。

```text
NEW_ARTICLE
  -> exact publisher article fetch
  -> in-memory article text extraction
  -> local Ollama structured summary
  -> GitHub Issue #242 comment delivery
  -> delivery marker verification boundary
  -> ack state update
  -> state commit
```

記事ごとにSHA-256由来のhidden delivery markerをIssue commentへ入れる。comment成功後・state保存前にrunnerが停止した場合、次runでmarkerを検出して再投稿せずackできる。

## Downstream delivery contract

各new articleを古い順に独立処理する。

1. `article_url` は `https://insight.factset.com` のみ許可する。
2. redirect後も同じpublisher domainに留まることを確認する。
3. 本文HTMLはsize上限付きで一時取得し、Gitへ保存しない。
4. `<article>`、次に `<main>`、最後にbody相当textの順で本文候補を抽出する。
5. 抽出本文が不足する場合はfail closedとし、通知もackもしない。
6. `qwen3:1.7b` に本文とtitleを渡し、JSON Schemaで日本語3〜5文を要求する。
7. 数値、比較条件、一時要因、会計上の特殊要因を優先し、本文にない因果・数値・投資推奨を生成させない。
8. 公開時刻をJSTへ変換し、元のUTC timestampも通知へ残す。
9. 原文URLを必ず通知へ残す。
10. GitHub Issue #242へのcomment成功後だけ個別にackする。
11. 配信失敗時はackしない。
12. 一部articleだけ成功した場合、成功済みだけstateへ反映し、失敗分は次tickで再試行する。

## Deployment canary

runtime導入時は既存feed全件を一括通知しない。初期cursorでは過去9件をbaseline済みとし、導入時点の最新1件だけをpendingに残してfull-path canaryとする。

canary成功後はそのarticleもackされ、以後は純粋な新着のみ通知される。

## Failure contract

以下はすべてfail closed。

- RSS fetch failure
- malformed XML
- empty RSS
- duplicate article identity
- title/link/published timestamp欠落
- delivery state欠落
- delivery state schema mismatch
- article fetch failure / off-domain redirect
- article body extraction failure
- local summarization failure
- GitHub delivery failure

feed failureを空feedや「新着なし」へ変換しない。delivery failureを「通知済み」に変換しない。

## Copyright / storage boundary

GitHubへ保存してよいもの:

- RSS metadata
- hashes / timestamps / provenance
- article URL
- operational delivery cursor
- 自分たちのderived summaryとclaim boundaries

保存しないもの:

- FactSet article本文全文
- 本文の大量な逐語転載

記事本文は通知生成時に一時取得し、分析後の永続成果は要約・source URL・delivery stateに限定する。

## Relationship to GDELT

`gdelt_news_discovery` はcompany-newsの**discovery-only** sourceであり、FactSet Insightと置換関係にない。

- GDELT: 広いニュース候補の発見
- FactSet Insight RSS: FactSetが公開したresearch articleの決定論的publisher feed

同じ記事がGDELTにも現れた場合、FactSet publisher URLを記事identity/sourceとして優先し、二重通知しない。

## Operational metrics

最低限、delivery runtimeで以下を出力する。

- `new_article_count`
- `fetch_failure`
- `parse_failure`
- `article_extract_failure`
- `summarization_failure`
- `delivery_failure`
- `delivered_count`
- `reused_delivery_count`
- `runtime_seconds`

定常時の正常系は `new_article_count=0` かつOllama未起動である。
