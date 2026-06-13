# src/preprocess/ CLAUDE.md

本モジュールはデータの前処理を担う。`io/` が提供する生データを、利用者が使いやすい形式へ整形する。

---

## 関心の分離 (Responsibility)
- **役割**: 生データのパース（解析）、計算、変換、およびダッシュボード用データの要約を担当する。
- **含まれるもの**: `text.ts` (XBRL解析), `edinet_data.ts`, `screener_data.ts` (データ集計)。

## 禁止事項 (Strict Rules)
- **直接通信の禁止**: 本モジュール内で `fetch` を実行してはならない。既に保存済みのデータのみを使用する。
- **UIロジックの排除**: HTML の生成などは行わず、純粋なデータ（JSON/オブジェクト）を返すことに専念する。

## 検証手順 (Verification)
- `bun run src/preprocess/text.ts` などを実行して、正しい中間データ（JSON形式等）が生成されることを確認する。
- 型定義が `shared/` と整合しているかを確認する。