# Edinet Financial Document Retrieval Skill

日本の金融庁が提供する EDINET (Electronic Disclosure for Investors' NETwork) から、有価証券報告書等の財務書類を効率的に取得・解析するための専門知見。

## 専門知識 (Expertise)
- **書類種別 (DocType)**: 有価証券報告書 (Annual Report), 四半期報告書 (Quarterly Report), 臨時報告書 (Extraordinary Report)。
- **検索ロジック**: `edinet_tickers.ts` を用いた証券コードから EDINET コードへの変換、日付範囲指定。
- **解析の癖**: XBRL パースの難易度、テキスト抽出時のノイズ除去、非構造化データの構造化。

## ワークフロー (Workflows)
1. **Ticker Mapping**: 証券コード (e.g., 7203) から EDINET 固有のコードを取得。
2. **Metadata Fetch**: 特定期間内の提出書類一覧を取得し、重要事象（M&A、提携等）をフィルタリング。
3. **Deep Extraction**: PDF/XBRL から特定の項目（事業等のリスク、経営方針等）を LLM で抽出。

## ベストプラクティス
- API への過度な負荷を避けるため、`jquants_cache_warm.ts` 等のキャッシュ機構を優先利用すること。
- 書類取得に失敗した場合は、指数関数的バックオフを用いてリトライすること。
