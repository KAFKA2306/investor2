# 📦 src/io/ CLAUDE.md なのだ！💕

ここは「外の世界」とやり取りする運び屋さんなのだ！📦
データを取ってくることだけに集中して、中身の難しいことは気にしないのだ✨🎀

---

## 🎯 関心の分離 (Responsibility)
- **役割**: APIやDBから「生のデータ（Raw Data）」を取得・保存すること。
- **含まれるもの**: `get.ts` (API Sync), クライアント定義など。

## ⚠️ 禁止事項 (Strict Rules)
- **加工の禁止**: データを「ととのえる（Preprocess）」ロジックをここに書いてはいけないのだ！❌ それは `preprocess/` のお仕事なのだ。
- **依存ルール**: `src/shared` だけを import していいのだ✨

## ✅ 検証手順 (Verification)
- `.env` に API キーが設定されているか確認するのだ。
- `bun run src/io/get.ts` を実行して、`raw` なデータがキャッシュされるか見るのだ！🎀
