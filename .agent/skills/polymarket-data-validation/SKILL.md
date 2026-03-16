---
name: polymarket-data-validation
description: Validate Polymarket event data integrity, detect anomalous odds, and ensure schema compliance before trading execution
---

# Polymarket Data Validation Skill

Polymarket の市場データ品質を確保し、異常値検出と整合性チェックを行うための専門知見。

## 専門知識 (Expertise)

- **スキーマ検証**: Zod による Polymarket イベント、オッズ、マーケットメタデータの型安全性確保。
- **異常検知**: オッズの統計的外れ値（Z-score > 3 σ）、流動性低下（bid-ask スプレッド拡大）、ブックのアンバランス検出。
- **整合性チェック**: イベント日時と現在時刻の乖離、複数ブックの同時引用、確率合計の逸脱（100% 超過等）。
- **データフレッシュネス**: キャッシュ更新タイムスタンプ、レート制限ウィンドウの監視。

## ワークフロー (Workflows)

1. **Inbound Validation**: API から受け取ったイベントデータが `PolymarketEventSchema` を満たすか即座にチェック。
2. **Anomaly Detection**: オッズ変動率、スプレッド、ボリュームプロファイルの統計的外れ値を検出。
3. **Cross-Book Coherence**: 複数マーケットメーカーのオッズが一貫性を保っているか（重大な乖離は alert）。
4. **Risk Flags**: 流動性不足、イベント直前での急激な変動等の取引リスク要因を自動抽出。

## ベストプラクティス

- 検証エラーは即座に propagate（suppress しない）。異常は早期に検出すべき。
- 複数の独立したチェック（スキーマ、統計、キャッシュ鮮度）を並行実行し、1 つでも失敗すれば REJECT。
- 検証パイプラインの出力は `CanonicalLog` 形式で記録し、後追い監査を可能にすること。
