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

persistent host上のstate例:

```text
/opt/data/cron/investor2_factset_delivery.json
```

このstateをGitHubのevidence artifactとして扱わない。

初回だけ、現在feedをbaselineとして明示的に既読化する。

```bash
python scripts/factset_insight_monitor.py bootstrap \
  --feed-json data/factset_insight/latest_feed.json \
  --state /opt/data/cron/investor2_factset_delivery.json
```

出力は `[SILENT]`。既存記事を初回に一括通知しない。

通常monitor:

```bash
python scripts/factset_insight_monitor.py monitor \
  --feed-json data/factset_insight/latest_feed.json \
  --state /opt/data/cron/investor2_factset_delivery.json
```

新着なし:

```text
[SILENT]
```

新着あり:

```text
NEW_ARTICLE\t{"article_id":"...","article_url":"...","author":"...","guid":"...","published_at":"...","title":"..."}
```

monitorはstateを変更しない。

## Downstream agent contract

`NEW_ARTICLE` が1件以上ある時だけLLM/agentを起動する。各articleを独立に処理する。

1. `article_url` から本文を取得する。
2. 本文取得に失敗したら通知せず、`ack`もしない。
3. 公開時刻をJSTへ変換する。元のUTC timestampも失わない。
4. 日本語で3〜5文に要約する。
5. 投資判断に効く数値、比較母集団、一時要因、除外時の値、会社名を優先する。
6. 要約はderived evidenceであり、FactSet本文そのものとして扱わない。
7. 原文URLを必ず通知へ残す。
8. 配信失敗時は`ack`しない。
9. 本文取得・要約・配信がすべて成功したarticleだけを個別に`ack`する。

成功後:

```bash
python scripts/factset_insight_monitor.py ack \
  --state /opt/data/cron/investor2_factset_delivery.json \
  --article-id '<article_id>'
```

複数articleのうち1件だけ失敗した場合、成功したarticleだけackする。失敗したarticleは次tickでも`NEW_ARTICLE`のまま残る。

## Failure contract

以下はすべてfail closed。

- RSS fetch failure
- malformed XML
- empty RSS
- duplicate article identity
- title/link/published timestamp欠落
- delivery state欠落（bootstrapしていない）
- delivery state schema mismatch
- article body extraction failure
- summary failure
- delivery failure

feed failureを空feedや「新着なし」へ変換しない。

## Copyright / storage boundary

GitHubへ保存してよいもの:

- RSS metadata
- hashes / timestamps / provenance
- article URL
- 自分たちのderived summaryとclaim boundaries

保存しないもの:

- FactSet article本文全文
- 本文の大量な逐語転載

記事本文は通知生成時に一時取得し、分析後の永続成果は要約・数値claim・source URLに限定する。

## Relationship to GDELT

`gdelt_news_discovery` はcompany-newsの**discovery-only** sourceであり、FactSet Insightと置換関係にない。

- GDELT: 広いニュース候補の発見
- FactSet Insight RSS: FactSetが公開したresearch articleの決定論的publisher feed

同じ記事がGDELTにも現れた場合、FactSet publisher URLを記事identity/sourceとして優先し、二重通知しない。

## Operational metrics

最低限、delivery runtimeで以下を記録する。

- `new_article_count`
- `fetch_failure`
- `article_extract_failure`
- `summary_failure`
- `delivery_failure`
- `runtime_seconds`

定常時の正常系は `new_article_count=0` かつagent未起動である。
