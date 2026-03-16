---
name: market-intelligence
description: Detect whale movements, latent economic signals, event-driven opportunities across on-chain and macro data
---

# Market Intelligence & Signal Detection Skill

オンチェーンデータ（クジラの動き）、ニュースイベント、および潜在的な経済シグナルを検出し、投資機会を特定するための専門知見。

## 専門知識 (Expertise)
- **Whale Watching**: 大口投資家のウォレット動向、CEX/DEX 間の資金移動、ステーブルコインの発行・回収。
- **Latent Signals**: 表層的なニュースの裏に隠れた経済的トレンド、セクター間の相関変化。
- **Event Analysis**: 決算発表、雇用統計、中央銀行の政策決定などのイベントが市場に与える短期・中期のインパクト評価。

## ワークフロー (Workflows)
1. **Trend Monitoring**: 主要なオンチェーン/オフチェーンデータソースの継続的監視。
2. **Contextualization**: 検出された事象を、現在のマクロ環境や過去の類似事例と照らし合わせて解釈。
3. **Signal Ranking**: 確信度、予想リターン、時間軸に基づいたシグナルの優先順位付け。

## ベストプラクティス
- シグナルは単一のソースに依存せず、常に複数の独立したソース（オンチェーンとオフチェーンの両方）で裏付けを取ること。
- 「偽のシグナル（ウォッシュトレード等）」を排除するためのフィルタリング基準を厳格に適用すること。

## 実装リファレンス (Implementation Reference)

### 利用可能なデータソース (Available Data Sources)
- **J-Quants**: 日本株データ、リアルタイム価格・マーケット指標
- **EDINET**: 日本の上場企業決算・監査報告書（`task edinet:fetch` で取得）
- **Fred Economic Data**: US マクロ経済指標（金利、失業率等）
- **Yahoo Finance**: グローバル株価・為替データ

### 実行コマンド (Commands)
```
task pipeline:verify          # パイプライン全体の整合性確認
task stats:summarize          # 市場統計サマリー生成
task polymarket:fetch         # Polymarket 予測市場データ取得
```

### エージェント連携
- **whale-watcher-agent**: 13F ファイリングから大口投資家のポジション変化を検出
- **macro-top-down-agent**: マクロ環境分析・セクター相関検出
- **event-driven-analyst-agent**: 短期イベント機会（スクイーズ候補、M&A レーダー）

### データ検証スキル
- 不整合検出: `polymarket-data-validation`
- スキーマ定義: `src/schemas.ts` 参照
