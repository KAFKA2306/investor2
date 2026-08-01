# AAARTS — 自律型アルファ研究システム

**公開ダッシュボード:** https://kafka2306.github.io/investor2/

AAARTS（Autonomous Agentic Alpha Trade System）は、投資仮説の登録、データ作成、検証、時系列のアウト・オブ・サンプル評価、再現可能な証拠の保存までを一つの研究サイクルとして管理するプロジェクトです。

単にバックテストの成績が良い候補を探すのではなく、**未来情報の混入を防ぎ、反証可能な条件を先に決め、同じ結果を再実行できる状態にすること**を重視します。

## 現在取り組んでいること

- EDINETの有価証券報告書を用いた企業業績予測
- 財務数値と開示文章の予測力を分離するアブレーション分析
- 不正会計検知と利益方向予測の評価
- 論文公開後の期間だけを使う凍結OOS検証
- 古典的な投資研究とファクター仮説の再現・失敗条件の記録
- 仮説、観測値、計算値、予測、判断を区別する証拠オントロジー

## このリポジトリで分かること

| 目的 | 主な入口 |
| --- | --- |
| 研究全体の進捗を見る | [Evidence & Evolution Dashboard](https://kafka2306.github.io/investor2/) |
| 論文構成を確認する | [NeurIPS earnings forecast outline](docs/paper/neurips_earnings_forecast_outline.md) |
| システム全体の流れを見る | [Simple flowchart](docs/diagrams/simpleflowchart.md) |
| アルファ探索の手順を見る | [Alpha discovery runbook](docs/specs/alpha_discovery_runbook.md) |
| OOS判定ルールを見る | [Time-tested alpha policy](docs/specs/time_tested_alpha_policy.md) |
| 複数論文の再検証結果を見る | [Multi-paper OOS summary](docs/research/multi_paper_oos_summary.md) |
| 運用上の禁止事項・作業規則を見る | [AGENTS.md](AGENTS.md) |
| 設計判断の履歴を見る | [ADR](docs/adr/) |

## 研究判定の原則

```text
仮説登録
  → データセット構築
  → 時点付き観測
  → モデル推定・予測
  → 凍結OOS・比較対象・アブレーション
  → 再現可能な証拠
  → candidate / reject / freeze_for_oos / promote / retire
```

`promote`は、インサンプル成績、説明のもっともらしさ、単独の好成績だけでは成立しません。時系列OOS、ベースライン比較、アブレーション、頑健性、再現性の証拠が必要です。

機械可読な定義は[`ontology/project.yaml`](ontology/project.yaml)にあります。

## セットアップ

```bash
task setup
cp .env.example .env
uv sync
```

## 実行

```bash
task run:newalphasearch  # 自律的なアルファ探索ループ
task view                # ダッシュボードとAPIを起動
```

## 現在の位置づけ

このリポジトリは研究・検証基盤です。掲載される仮説や評価は、売買推奨や将来収益の保証ではありません。

**README最終監査:** 2026-08-01
