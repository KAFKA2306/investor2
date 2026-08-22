# AAARTS — 投資仮説を反証可能にする研究基盤

[![Quality Gates](https://github.com/KAFKA2306/investor2/actions/workflows/quality.yml/badge.svg)](https://github.com/KAFKA2306/investor2/actions/workflows/quality.yml)
[![Validate and deploy dashboard](https://github.com/KAFKA2306/investor2/actions/workflows/pages.yml/badge.svg)](https://github.com/KAFKA2306/investor2/actions/workflows/pages.yml)
[![Verify deployed GitHub Pages](https://github.com/KAFKA2306/investor2/actions/workflows/live-pages-smoke.yml/badge.svg)](https://github.com/KAFKA2306/investor2/actions/workflows/live-pages-smoke.yml)

`investor2` は、投資仮説・point-in-time evidence・OOS検証・判断記録を一つの追跡可能な流れで扱う研究repositoryです。

**バックテストの好成績だけでは採用しません。** 仮説と反証条件を先に固定し、その時点で利用可能だったデータ、比較対象、取引コスト、OOS結果、判断理由まで再実行可能な証拠として残します。

公開ダッシュボード: https://kafka2306.github.io/investor2/

## Canonical flow

```text
一次情報 / revision固定データ
  -> input ledger / snapshot
  -> hypothesis + falsifiers
  -> point-in-time dataset
  -> OOS / baseline / ablation / costs
  -> reproducible evidence
  -> Decision Snapshot
  -> 人間の投資判断
  -> Decision Review
```

正準仕様: [Canonical investment flow](docs/architecture/canonical-investment-flow.md)

## Commands

```bash
task setup               # locked dependencies + prek
task check               # canonical non-mutating quality gate
task run:newalphasearch  # frozen real-data hypothesis validation
task dashboard:dev       # local evidence dashboard
```

実行入口は `Taskfile.yml` を正準とします。別名CLIや並行pipelineは、実際の運用コストを下げる場合を除いて追加しません。

## Research rules

- future informationを混ぜない。
- 結果を見る前に仮説・比較対象・失敗条件を固定する。
- source revision / query / period / unit / hash を追跡可能にする。
- OOS、baseline、ablation、取引コストを直接検証する。
- 良い結果だけでなく、棄却された仮説も結果として保存する。
- `candidate` やDecision Snapshot eligibilityを売買推奨とみなさない。

投資戦略では、該当する場合に after-cost return/P&L、Sharpe、maximum drawdown、beta/correlation、turnover/exposure、benchmark comparison、tested capital scale を直接評価します。

## Main surfaces

| 目的 | 正準入口 |
| --- | --- |
| 研究全体を見る | [Evidence & Evolution Dashboard](https://kafka2306.github.io/investor2/) |
| 仮説探索 | [Hypothesis Lab](docs/research/hypothesis-lab.md) |
| 入力→検証→判断 | [Canonical investment flow](docs/architecture/canonical-investment-flow.md) |
| 判断時点の固定 | [Decision ledger](data/decision_ledger/README.md) |
| Alpha探索手順 | [Alpha discovery runbook](docs/specs/alpha_discovery_runbook.md) |
| OOS判定 | [Time-tested alpha policy](docs/specs/time_tested_alpha_policy.md) |
| 外部snapshot | [External snapshot store](docs/specs/external_snapshot_store.md) |
| repository運用 | [AGENTS.md](AGENTS.md) |

## EDINET-Bench

`industry_prediction` は公式test splitを持たないため、正式評価では固定manifestを使用します。

- manifest: `data/benchmarks/industry_prediction_frozen_split.json`
- source revision / Parquet SHA-256 / row countを固定
- developmentとfrozen evaluationを決定論的に分離
- source driftやmanifest不整合ではfail closed

## Positioning

このrepositoryは研究・検証基盤です。未実証のalpha性能や将来収益を主張しません。価値は、研究結果を疑い、再実行し、どの証拠からどの判断に至ったかを後から反証できる状態にあります。
