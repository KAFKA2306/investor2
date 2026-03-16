---
name: polymarket-alpha-miner
description: Extract time-series alpha signals from Polymarket event calendars, implied probabilities, and order flow dynamics specific to prediction markets
---

# Polymarket Alpha Miner Skill

Polymarket のイベントカレンダー、インプライド確率、オーダーフロー等から、予測市場特有の時系列シグナルを抽出するための専門知見。

## 専門知識 (Expertise)

- **イベントカレンダー相関**: 決算発表、政策決定、スポーツイベント等の実現時刻と市場心理の変化を捉える。
- **インプライド確率抽出**: オッズ（例： YES = 0.65, NO = 0.35）から、市場参加者の内在期待確率を逆算。
- **流動性スケア**: マーケット深さ（Depth）とボリュームベース調整。流動性が薄い場合の信号の信頼度低下を定量化。
- **オーダーフロー分析**: 大口買い・売りの時系列パターン（VWAP との乖離等）から、情報優位性の時間窓を推定。

## ワークフロー (Workflows)

1. **Event Calendar Scanning**: 今後 N 日間のイベント、過去同時期のマーケット動向を検索。
2. **Implied Probability Decomposition**: オッズから市場予想確率を算出、過去の実現頻度との乖離を計算（期待値）。
3. **Order Flow Fingerprinting**: ブロック取引（大口）の時系列、価格インパクトを分析して、インサイダー情報を示唆するシグナルを検出。
4. **Signal Strength Ranking**: イベント邁進度、流動性、ヒストリカル的中率に基づき、シグナルの信頼度スコアを出力。

## ベストプラクティス

- Polymarket のシグナルは「短期（< 1 週間）の Alpha」に特化。長期的なファンダメンタル分析の補足的な役割に留める。
- 流動性が著しく低いマーケット（< $100k ADV）は、統計的信頼度の低さから signal generation の対象外とすること。
- オーダーフロー分析は必ず複数時間枠（1 分、5 分、1 時間）で実施し、ノイズフロアと真のシグナルを区別。
