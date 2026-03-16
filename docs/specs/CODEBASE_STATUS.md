# 📋 Codebase Status Report

**最終更新**: 2026-03-17

このドキュメントは、実装済みコードと未実装（aspirational）の機能を明確に分離する実装マップです。

---

## 🏗️ 実装済みファイル一覧

### Core System & Config
| ファイル | 行数 | 役割 | 状態 |
|---|---|---|---|
| `config/default.yaml` | ~288 | 統合パス管理（SSOT） | ✅ 実装 |
| `src/shared/schema.ts` | ~28 | ConfigSchema, 型定義 | ✅ 実装 |
| `Taskfile.yml` | ~703 | 全タスク定義 | ✅ 実装 |

### I/O Layer
| ファイル | 行数 | 役割 | CDD違反 | 状態 |
|---|---|---|---|---|
| `src/io/get.ts` | 全体 | J-Quants / EDINET 取得 | ハードコードパス | ⚠️ 部分 |

### Preprocessing Layer
| ファイル | 行数 | 役割 | CDD違反 | 状態 |
|---|---|---|---|---|
| `src/preprocess/edinet.ts` | ~200+ | EDINET 企業情報解析 | L4 ハードコード | ⚠️ 部分 |
| `src/preprocess/text.ts` | 全体 | XBRL テキスト抽出 | ハードコードパス | ⚠️ 部分 |
| `src/preprocess/screener.ts` | 全体 | スクリーナーデータ集計 | ハードコードパス | ⚠️ 部分 |

### Dashboard (UI)
| ファイル | 行数 | 役割 | CDD違反 | 状態 |
|---|---|---|---|---|
| `src/dashboard/server.ts` | ~1328 | Hono HTTP サーバー | L17 ハードコード | ⚠️ 部分 |
| `src/dashboard/package.json` | - | Vite + Tailwind UI | - | ✅ 実装 |

### Tasks
| ファイル | 行数 | 役割 | CDD違反 | 状態 |
|---|---|---|---|---|
| `src/tasks/stats.ts` | ~150+ | キャッシュ統計生成 | L26 ハードコード | ⚠️ 部分 |

---

## 🔴 Taskfile タスク vs ファイルマッピング

### 実装済み（✅）
| Taskfile タスク | バッキングスクリプト | 実装パス |
|---|---|---|
| `get:all` | `bun src/io/get.ts` | ✅ 存在 |
| `edinet:fetch:all` | `GET_MODE=edinet bun src/io/get.ts` | ✅ 存在 |
| `jquants:fetch:latest` | `GET_MODE=jquants bun src/io/get.ts` | ✅ 存在 |
| `qa` / `check` | `bun run format/lint` | ✅ 存在 |
| `pipeline:*` | 各種 experiments scripts | ✅ 存在（investor repo 依存） |
| `run:newalphasearch` | Loop + experiments runner | ✅ 存在（investor repo 依存） |

### 未実装（❌）
| Taskfile タスク | 期待パス | 実装状態 | 代替手段 |
|---|---|---|---|
| `cache:view` | `src/tasks/print_cache_statistics.ts` | ❌ 未実装 | `server.ts` の統計表示 |
| `preprocess:stats` | `src/preprocess/stats_cache.ts` | ❌ 未実装 | `src/tasks/stats.ts` 参照 |
| `preprocess:edinet:xbrl:text` | `src/preprocess/edinet_xbrl_text_extraction.ts` | ❌ 未実装 | `src/preprocess/text.ts` 参照 |
| `dashboard:dev` | `src/dashboard/investor_dashboard_server.ts` | ❌ 未実装 | `src/dashboard/server.ts` 参照 |

**注記**: `dashboard:dev` は Taskfile.yml L46-50 で参照されていますが、実装は `src/dashboard/server.ts` にあります。

---

## 🚨 既知のハードコード箇所

現在、以下のファイルで `/mnt/d/investor_all_cached_data` がハードコード（config.yaml との分離）されています：

| ファイル | 行 | コード | 推奨修正 |
|---|---|---|---|
| `src/dashboard/server.ts` | 17 | `const CACHE_ROOT = "/mnt/d/..."` | config.default.yaml から取得 |
| `src/preprocess/edinet.ts` | 4 | `const CACHE_ROOT = "/mnt/d/..."` | config.default.yaml から取得 |
| `src/tasks/stats.ts` | 26 | `const CACHE_ROOT = "/mnt/d/..."` | config.default.yaml から取得 |
| `src/preprocess/text.ts` | TBD | EDINET テキスト処理 | config.default.yaml から取得 |
| `src/io/get.ts` | TBD | J-Quants / EDINET 取得 | config.default.yaml から取得 |
| `src/preprocess/screener.ts` | TBD | スクリーナー処理 | config.default.yaml から取得 |

---

## 📊 パイプライン依存関係

```
investor2 リポジトリ:
  src/io/get.ts (J-Quants, EDINET 取得)
    ↓
  src/preprocess/ (テキスト抽出、企業情報解析)
    ↓
  src/dashboard/server.ts (統計・企業情報表示)

Taskfile 実行:
  task get:all                        (src/io/get.ts)
  task cache:view ❌ 未実装
  task preprocess:stats ❌ 未実装
  task dashboard:dev ❌ 未実装

investor リポジトリ （別リポジトリ、パイプラインメイン）:
  ts-agent/ (alpha discovery pipeline)
    - experiments:* scripts
    - run:newalphasearch loop
    - pipeline:mine / pipeline:verify
```

---

## 🔮 Aspirational Features（未実装）

以下は `docs/specs/` 他で説明されているが、実装は**存在しません**：

### Frontend (見積: 2026年Q2)
- Alpha Discovery View（新アルファ表示）
- Kill Switch（取引停止ボタン）
- Execution Management View（約定管理）
- Performance Audit View（パフォーマンス監査）
- Risk Guardian（リスク表示）

### Data Pipeline (見積: 2026年Q2)
- PathRegistry (`src/system/path_registry.ts`)
- Layer 3-5 EDINET Analysis（itemization, KG, AI-Exposure）
- verify_edinet_io_contract.ts

### EDINET MCP Tools（見積: 2026年Q2）
- Itemization Engine
- Knowledge Graph Builder
- AI-Exposure Calculator
- verify_edinet_io_contract.ts

---

## 📐 CDD（Crash-Driven Development）レビュー

### 要件
- ❌ `try-catch` なし（ビジネスロジック層）
- ❌ Defensive returns（`null` / `false` など）
- ❌ 例外抑制（ロギング代替）
- ✅ スタックトレース完全出力

### 現状
- ⚠️ ハードコードパスが存在（修正待ち）
- ⚠️ 一部タスク定義と実装ファイルの不一致（Taskfile L46-50）

---

## 🔧 チェックリスト：新コード追加時

```bash
# 1. ハードコード検索
grep -r "/mnt/d/investor" src/ --include="*.ts" | wc -l

# 2. config.yaml 参照
grep -r "config.paths" src/ --include="*.ts" | wc -l

# 3. Taskfile タスク妥当性確認
task --list-all | grep "cache:view\|preprocess:stats\|dashboard:dev"
```

---

## 📖 関連ドキュメント

- `DATA_STRUCTURE.md` — パス管理の現状
- `OPERATIONS.md` — タスク実行ガイド
- `EDINET.md` — EDINET パイプライン詳細
- `Frontend.md` — UI 実装状況
- `db.md` — データベーススキーマ

