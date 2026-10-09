# Japan Yen Equity Monitor

Issue: #423

## Purpose

円高局面で確認している日本株15銘柄について、J-Quantsを使わずに同一ルールで市場反応・長期ファンダ・決算イベントを取得する。

このpipelineは売買シグナルではない。取得結果を `investor2` の external snapshot contractに載せ、後続の仮説検証で再利用できる入力を作る。

## Canonical watchlist

`config/japan_yen_watchlist.json`

日本株tickerは Yahoo Finance/yfinance互換の `####.T` のみを許可する。`TYO:####` は受け付けない。

## Sources and roles

| Source | Role | Authority boundary |
| --- | --- | --- |
| Yahoo Finance chart endpoint | 終値・出来高・5-session/1M/3M return、USD/JPY | 市場観測。取得失敗を0補完しない |
| The社史 | 10年比較、ROE、PER/PBR、利益率、CAGR | 長期比較用の二次集約。決算判断の一次authorityにはしない |
| 株探 | 決算・業績修正・配当修正のイベント発見 | discovery。数値判断は各社IRで再確認する |
| 各社IR | 最新決算値・会社予想・配当の最終確認 | primary authority |

## Return convention

- 5 sessions: 最新観測から5取引観測前
- 1M: 最新日から1 calendar month戻した日以前の直近実在観測
- 3M: 最新日から3 calendar months戻した日以前の直近実在観測

休日を株価0や架空の取引日で埋めない。

## Run

Narrow fetch without registration:

```bash
task market:japan-yen:fetch
```

Full fetch and canonical snapshot registration:

```bash
task market:japan-yen:snapshot
```

The snapshot command refuses catalog registration when Yahoo market data for any watchlist symbol or USD/JPY is unavailable. The社史 / 株探の補助データ欠損は `errors` に残し、observed valueへ昇格しない。

## Artifact

`data/snapshots/japan_yen_equity_monitor_<retrieved_at>.json`

Schema: `investor2.japan-yen-equity-monitor.v1`

Each artifact keeps:
- exact watchlist
- market observations and return anchors
- USD/JPY
- The社史 metrics
- 株探 discovered headlines
- errors
- retrieval timestamp
- source URLs / scope

Registered snapshots use:
- dataset id: `japan_yen_equity_monitor`
- reuse key: `market/japan/yen-beneficiary-watchlist`
- source: `public_web_research`

## Verification

```bash
uv run --no-sync pytest tests/test_japan_equity_monitor.py
task data:snapshots:audit
task check
```

Live source layout can change. Parser failure must remain explicit; do not repair a failed parse by inventing values.
