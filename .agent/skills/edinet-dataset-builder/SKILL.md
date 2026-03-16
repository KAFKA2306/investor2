---
name: edinet-dataset-builder
description: Build PIT-clean time-series financial datasets from EDINET documents with handling of missing values, corporate actions, and cross-period alignment. Use when constructing historical financial data for backtesting, aligning quarterly/annual statements into continuous time-series, handling corporate actions (splits, mergers) with point-in-time accuracy, or preparing training data for machine learning models.
---

# EDINET Dataset Builder Skill

EDINET から取得した複数期間の財務データを、Point-in-Time (PIT) クリーニング と時系列統合を行い、分析用データセットを構築するための専門知見。

## 専門知識 (Expertise)

- **PIT クリーニング**: 決算発表日を基準に、各データポイントの有効期限（知られていた情報のみ使用）を厳格に管理。
- **欠損値処理**: 未報告項目、提出遅延、フォーマット変更に対応。補間か除外かを文脈に応じて判定。
- **企業行動調整**: 株式分割、増減資、M&A の前後でデータスケーリングを正確に行う。
- **時系列マージ**: 複数の報告書形式（年報、四半期報、臨時報）を統一的な時系列に統合。

## ワークフロー (Workflows)

1. **Metadata Extraction**: 各 EDINET 書類から発表日、基準日、会計期間を抽出。
2. **Data Standardization**: 会計基準の変更（IFRS 移行等）に対応し、単一の会計系統に統一。
3. **Corporate Actions Registry**: 配当支払日、分割実施日等のイベント列から、データ調整係数を計算。
4. **Time-Series Assembly**: 欠損を埋めつつ、PIT ルールに基づき有効データのみを時系列として出力。

## ベストプラクティス

- データ調整係数（例：分割比率）は常にメタデータとして保持し、後から追跡可能にすること。
- PIT ルール違反（未来情報の混入）は自動検出し、該当区間を quarantine すること。
- キャッシュ層（`SQLite` 等）で処理済みの書類とそのバージョンを管理し、重複処理を回避。
