# 📍 統合データ管理構造 (Unified Data Path Architecture)

> **重要**: このドキュメントは、全データ・ログの唯一の真実の源（Single Source of Truth）です。
> このファイルを読まずに直接パスをハードコードしてはいけません！❌

**最終更新**: 2026-03-17 | **実装状況**: ⚠️ 部分実装（PathRegistry未実装、ハードコード残存）

---

## 🗂️ ディレクトリ構造

全データは以下の一元ロケーションに統合されています：

```
/mnt/d/investor_all_cached_data/          ← マスターベース
├── jquants/                              ← J-Quants マーケットデータ (1.6 GB)
│   ├── raw_stock_price.csv(.gz)         # 株価データ
│   ├── raw_stock_fin.csv(.gz)           # 財務データ
│   ├── stock_list.csv(.gz)              # 銘柄リスト
│   ├── stock_labels.csv(.gz)            # ラベル
│   └── raw_statements/                  # 決算書アーカイブ
│
├── cache/                                ← SQLite キャッシュ層 (690 MB)
│   ├── market_cache.sqlite              # マーケット API キャッシュ
│   ├── marketdata.sqlite                # マーケットデータ キャッシュ
│   ├── http_cache.sqlite                # HTTP キャッシュ
│   ├── yahoo_finance_cache.sqlite       # Yahoo Finance キャッシュ
│   ├── jquants_pead_cache.sqlite        # PEAD 特異性 キャッシュ
│   ├── uqtl.sqlite                      # UQTL イベント ストア
│   ├── alpha_knowledgebase.sqlite       # Alpha Knowledge Base
│   └── memory.sqlite                    # MemoryCenter (実験履歴)
│
├── edinet/                               ← EDINET 専用ストレージ (599 MB)
│   ├── cache.sqlite                     # EDINET API キャッシュ
│   ├── search.sqlite                    # 全文検索インデックス
│   └── docs/                            # DL済み決算書ドキュメント
│
├── outputs/                              ← パイプライン出力アーティファクト (33 MB)
│   ├── standard_verification_data.json  # 検証マトリックス
│   ├── standard_verification_data.png   # 検証プロット
│   ├── VERIF_*.png                      # 個別アルファ検証プロット
│   ├── KB_BACKTEST_*.png                # Knowledge Base バックテスト結果
│   ├── playbook.yaml                    # コンテキスト ACE プレイブック
│   ├── multi_faceted_proof.json         # マルチレイヤー検証証拠
│   └── plot_data_*.json                 # 可視化用データ
│
├── preprocessed/                         ← 前処理済みデータセット (26 MB)
│   ├── edinet_governance_map.json       # ガバナンス・インテリジェンス
│   ├── edinet_10k_intelligence_map.json # 10K フィーチャーセット
│   └── macro_indicators_map.json        # マクロ経済指標マップ
│
└── logs/                                 ← 監査・実行ログ (856 KB)
    ├── unified/                         # alpha_discovery_*.json (メインアルファログ)
    ├── experiments/                     # マイニング実験 report.json
    ├── verification/                    # 検証詳細ログ
    ├── benchmarks/                      # ベンチマーク結果
    ├── workflows/                       # ワークフロー実行ログ
    └── mission.md                       # ミッション監査ログ
```

---

## 🔗 パス管理（現状）

### ✅ 真実の源 (SSOT): config/default.yaml

現在、`config/default.yaml` の `paths:` セクションがパスの唯一の正しい源です。

```yaml
paths:
  # Core roots (new centralized location)
  data: /mnt/d/investor_all_cached_data/jquants
  logs: /mnt/d/investor_all_cached_data/logs
  verification: /mnt/d/investor_all_cached_data/outputs
  cache: /mnt/d/investor_all_cached_data/cache
  edinet: /mnt/d/investor_all_cached_data/edinet
  preprocessed: /mnt/d/investor_all_cached_data/preprocessed
  # ... 約25個のサブパスキー
```

### ⚠️ 未実装: PathRegistry

`src/system/path_registry.ts` は**未実装**です。将来のリファクタリング時に以下を検討してください：

```typescript
// 理想形（未実装）
import { ConfigSchema } from '../shared/schema.ts';
import yaml from 'js-yaml';

const config = ConfigSchema.parse(
  yaml.load(readFileSync('config/default.yaml'))
);

// 使用例
const dataPath = config.paths.data;
const cachePath = config.paths.cache;
```

### ❌ 既知のハードコード箇所（修正待ち）

現在、以下のファイルで `/mnt/d/investor_all_cached_data` がハードコードされています：

| ファイル | 行 | 説明 |
|---|---|---|
| `src/dashboard/server.ts` | 17 | `const CACHE_ROOT = "/mnt/d/investor_all_cached_data"` |
| `src/preprocess/edinet.ts` | 4 | `const CACHE_ROOT = "/mnt/d/investor_all_cached_data"` |
| `src/tasks/stats.ts` | 26 | `const CACHE_ROOT = "/mnt/d/investor_all_cached_data"` |
| `src/preprocess/text.ts` | TBD | EDINET テキスト抽出 |
| `src/io/get.ts` | TBD | データ取得 |
| `src/preprocess/screener.ts` | TBD | スクリーナーデータ |

**推奨**: ConfigSchema 経由でパスを取得する標準パターンを採用する（将来）。

---

## 📋 チェックリスト：新コード追加時

新しいデータアクセスコードを追加する場合は、**必ず**以下をチェック：

- [ ] ハードコードされたパスがないか検索: `grep -r "/mnt/d" src/ --include="*.ts"` ❌
- [ ] 相対パスや `process.cwd()` ベースのパス推測がないか確認 ❌
- [ ] `config/default.yaml` に新しいパスが必要な場合は記載 ✅
- [ ] **将来**: PathRegistry 実装後は、ConfigSchema 経由でパスを取得 ✅


---

## 📖 関連ドキュメント

- `config/default.yaml` — パス設定の真実の源
- `src/shared/schema.ts` — ConfigSchema 定義
- `CLAUDE.md` — プロジェクト全体の指針
- `docs/specs/CODEBASE_STATUS.md` — 実装済み・未実装の ファイル一覧

