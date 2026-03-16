# 🪄 src/preprocess/ CLAUDE.md なのだ！💕

ここはデータの「魔法の仕立て屋」なのだ！🪄
`io/` が持ってきた生のデータを、みんなが使いやすいようにピカピカにするのだ✨🎀

---

## 🎯 関心の分離 (Responsibility)
- **役割**: 生データのパース（解析）、計算、変換、およびダッシュボード用データの要約。
- **含まれるもの**: `text.ts` (XBRL解析), `edinet_data.ts`, `screener_data.ts` (データ集計)。

## ⚠️ 禁止事項 (Strict Rules)
- **直接通信の禁止**: ここで `fetch` してはいけないのだ！❌ 使うのはすでに保存されたデータだけなのだ。
- **UIロジックの排除**: HTMLの生成などはここで行わず、Pureなデータ（JSON/Object）を返すことに専念するのだ！

## ✅ 検証手順 (Verification)
- `bun run src/preprocess/text.ts` などで、正しい中間データ（JSON等）が生成されるか確認するのだ！🎀
- 型定義が `shared/` と合っているかチェックするのだ✨
