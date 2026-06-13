# src/shared/ CLAUDE.md

本ディレクトリはプロジェクトの基盤である。すべてのコードはここを参照するが、外部に依存せず、堅牢性を確保することを意図している。

---

## 関心の分離 (Responsibility)
- **役割**: プロジェクト全体で共有される「型（Type）」および「定義（Schema）」を管理する。
- **含まれるもの**: `schema.ts`（Zod Schema）、`types.ts` など。

## 禁止事項 (Strict Rules)
- **他者への依存の禁止**: `src/io`、`src/preprocess` などをインポートしてはならない。
- **ロジックの排除**: ここには複雑な副作用（DB操作やAPI通信）を書かない。データ構造のみに専念する。

## 検証手順 (Verification)
- `bun x tsc --noEmit` が型エラーを発生させないことを確認する。