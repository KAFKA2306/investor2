# 🏠 src/shared/ CLAUDE.md なのだ！💕

ここはプロジェクトの「土台」なのだ！✨
すべてのコードがここを参照するけど、ここは誰にも頼らない、強い心を持ってるのだ！🎀

---

## 🎯 関心の分離 (Responsibility)
- **役割**: プロジェクト全体で共有される「型（Type）」や「定義（Schema）」を管理するのだ。
- **含まれるもの**: `schema.ts` (Zod Schema), `types.ts` など。

## ⚠️ 禁止事項 (Strict Rules)
- **他への依存禁止**: `src/io`, `src/preprocess` などを import してはいけないのだ！❌
- **ロジックの排除**: ここには複雑な副作用（DB操作やAPI通信）を書かないのだ！データ構造だけに専念するのだ✨

## ✅ 検証手順 (Verification)
- `bun x tsc --noEmit` で型エラーが出ないことを確認するのだ！🎀
