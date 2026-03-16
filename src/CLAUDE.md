# 🎀 src/ の歩きかた (CLAUDE.md) なのだ！💕

このディレクトリは `investor2` プロジェクトの心臓部なのだ✨
機能ごとにフォルダが分かれていて、きれいに整理されているのだ！🎀

---

## 📂 ディレクトリの役割なのだ！

- **[shared/](./shared/CLAUDE.md)**: みんなで使う「きほん」の設定や型（Schema）が入ってるのだ✨
- **[io/](./io/CLAUDE.md)**: お外（API）からデータを取ってくる「運び屋さん」なのだ📦
- **[preprocess/](./preprocess/CLAUDE.md)**: とってきたデータを使いやすく「おめかし」する魔法の部屋なのだ🪄
- **[dashboard/](./dashboard/CLAUDE.md)**: きれいにしたデータをみんなに見せる「舞台（UI）」なのだ🚀
- **[tasks/](./tasks/CLAUDE.md)**: 統計を取ったりする「裏方のお仕事」なのだ📊

---

## � 依存の順番 (Dependency Order) なのだ！💕

コードの依存関係は**「一方通行」**が鉄則なのだ！下に行くほど独立性が高くなるのだ✨

1. **`dashboard/`** (一番上) -> `preprocess/` や `io/`, `shared/` を使えるのだ！
2. **`preprocess/`** -> `io/` や `shared/` を使えるのだ！ (`dashboard/` に依存しちゃダメ❌)
3. **`io/`** -> `shared/` だけを使えるのだ！ (`preprocess/` や `dashboard/` に依存しちゃダメ❌)
4. **`shared/`** (基盤) -> 誰にも依存しないのだ！孤高の存在なのだ👑

※ **`tasks/`** は独立したバッチ処理だから、必要に応じて全体を使えるけど、他の機能が `tasks/` に依存するのはNGなのだ！

---

## �🛠️ 基本的な動かし方なのだ！

プロジェクト全体を動かすときは、ルートにある `Taskfile.yml` を使うのがプロのやりかたなのだ✨

- **ビルドチェック**: `bun x tsc --noEmit`
- **サーバー起動**: `bun run src/dashboard/server.ts`
- **データ取得**: `bun run src/io/get.ts`

各フォルダの中にも `CLAUDE.md` があるから、詳しい使い方はそっちを見てね！💕✨
