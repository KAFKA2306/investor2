# src/dashboard/ CLAUDE.md

本ファイルはプロジェクトのUI（ダッシュボード）に関する説明である。`preprocess/` が作成した整形済みデータを、閲覧者にとって見やすく表示する。

---

## 関心の分離 (Responsibility)

- **役割**: HTTPサーバーの提供、HTMLのレンダリング、およびユーザー体験（UX）の管理。

- **含まれるもの**: `server.ts` (Hono Server)。

---

## 禁止事項 (Strict Rules)

- **生データへのアクセス禁止**: `io/` が取得した生データ（CSVやDB）をここで直接加工してはならない。代わりに `preprocess/` の関数を呼ぶ。

- **ビジネスロジックの排除**: 複雑な計算やデータ変換はここでは行わず、表示用の加工のみとする。

---

## 検証手順 (Verification)

- `bun run src/dashboard/server.ts` でサーバーがエラーなく起動するかを確認する。

- ブラウザで `localhost` に接続して、表示が崩れていないことを確認する。