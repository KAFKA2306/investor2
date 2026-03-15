---
name: polymarket-expert
description: Specialized knowledge for analyzing prediction markets on Polymarket. Use this when the user asks to evaluate betting odds, calculate expected value, execute CLOB orders, or formulate Kelly-optimal betting strategies for specific events.
---

# Polymarket Trading Bot Skill

Polymarket の CLOB (Central Limit Order Book) と連携し、効率的な予測市場取引を行うための専門知見。

## 専門知識 (Expertise)
- **CLOB API の特性**: レート制限 (Rate Limits) の遵守、署名済み注文 (Signed Orders) の生成、ガスレス注文の管理。
- **ベッティング戦略**: ケリー基準に基づく資金管理、オッズ歪みの検出、イベントドリブンなポジション解消。
- **データ構造**: Zod スキーマを用いた Polymarket 固有のメッセージングのバリデーション。

## ワークフロー (Workflows)
1. **Market Discovery**: 進行中のイベント、流動性の高いマーケットの抽出。
2. **Backtesting**: `backtest_core.ts` を用いた過去データの検証手順。
3. **Execution**: ポジションのオープン、指値注文の更新、ストップロスの設定。

## ベストプラクティス
- ポジションのオープン前には必ず `polymarket_schemas.ts` でデータ整合性を検証すること。
- テレメトリログは `telemetry_logger.ts` を通じて記録し、異常検知を自動化すること。
