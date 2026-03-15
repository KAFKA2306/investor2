---
name: edinet-expert
description: Expertise for retrieving and parsing financial disclosure documents from EDINET. Use this when the user asks to search for Japanese corporate reports, parse XBRL, or extract specific sections from annual and quarterly statements.
---

# Edinet Financial Document Retrieval Skill

日本の金融庁が提供する EDINET から、有価証券報告書等の財務書類を効率的に取得・解析するための専門知見。

## 専門知識 (Expertise)
- **書類種別 (DocType)**: 有価証券報告書 (Annual Report), 四半期報告書 (Quarterly Report), 臨時報告書 (Extraordinary Report)。
- **検索ロジック**: `edinet_tickers.ts` を用いた証券コードから EDINET コードへの変換、日付範囲指定。

## ワークフロー (Workflows)
1. **Ticker Mapping**: 証券コード (e.g., 7203) から EDINET 固有のコードを取得。
2. **Metadata Fetch**: 特定期間内の提出書類一覧を取得し、重要事象をフィルタリング。
3. **Deep Extraction**: PDF/XBRL から特定の項目（事業等のリスク、経営方針等）を LLM で抽出。
