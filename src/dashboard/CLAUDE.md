# 🚀 src/dashboard/ CLAUDE.md なのだ！💕

ここはプロジェクトの「看板（UI）」なのだ！🚀
`preprocess/` が作ってくれたキレイなデータを、みんなに見やすく表示するのだ✨🎀

---

## 🎯 関心の分離 (Responsibility)
- **役割**: HTTPサーバーの提供、HTMLのレンダリング、およびユーザー体験（UX）の管理。
- **含まれるもの**: `server.ts` (Hono Server)。

## ⚠️ 禁止事項 (Strict Rules)
- **生データへのアクセス禁止**: `io/` が持ってきた生のCSVやDBをここで直接こねくり回してはいけないのだ！❌ `preprocess/` の関数を呼ぶのだ！
- **ビジネスロジックの排除**: 複雑な計算やデータ変換はここでは行わず、表示用の加工だけにするのだ✨

## ✅ 検証手順 (Verification)
- `bun run src/dashboard/server.ts` でサーバーがエラーなく立ち上がるか見るのだ！🚀
- ブラウザで `localhost` に繋いで、画面が崩れていないかチェックなのだ！🎀
