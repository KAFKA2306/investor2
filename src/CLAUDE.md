# src/ の歩き方 (CLAUDE.md) である

このディレクトリは `investor2` プロジェクトの中核を成す。機能ごとにフォルダが分割されており、整理されている。

---

## ディレクトリの役割

- **[shared/](./shared/CLAUDE.md)**: 共通で使用される基本的な設定や型（Schema）が含まれている。  
- **[io/](./io/CLAUDE.md)**: 外部 API からデータを取得する役割を担う。  
- **[preprocess/](./preprocess/CLAUDE.md)**: 取得したデータを利用しやすい形へ整形する処理を担う。  
- **[dashboard/](./dashboard/CLAUDE.md)**: 整形済みデータを表示・可視化するユーザーインターフェースを提供する。  
- **[tasks/](./tasks/CLAUDE.md)**: 統計処理やバッチ処理を担当する。

---

## 依存の順番（Dependency Order）

コードの依存関係は一方向性が原則であり、下位に位置するモジュールほど独立性が高まる。

1. **`dashboard/`（最上位）** は `preprocess/`、`io/`、`shared/` を使用できる。  
2. **`preprocess/`** は `io/` および `shared/` を使用できる（`dashboard/` には依存しない）。  
3. **`io/`** は `shared/` のみを使用できる（`preprocess/` や `dashboard/` には依存しない）。  
4. **`shared/`** は基盤として、他のモジュールに依存されることはない。

※ `tasks/` は独立したバッチ処理であり、必要に応じて全体から利用可能であるが、他の機能が `tasks/` に依存することは許容されない。

---

## 基本的な動かし方

プロジェクト全体を実行するには、ルートにある `Taskfile.yml` を使用するのが標準的な方法である。

- **ビルドチェック**: `bun x tsc --noEmit`  
- **サーバー起動**: `bun run src/dashboard/server.ts`  
- **データ取得**: `bun run src/io/get.ts`

各フォルダには `CLAUDE.md` が含まれているため、詳しい使用方法はそちらを参照すること。