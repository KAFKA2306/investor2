# 📍 統合データ管理構造 (Unified Data Path Architecture)

> **重要**: このドキュメントは、全データ・ログの唯一の真実の源（Single Source of Truth）です。
> このファイルを読まずに直接パスをハードコードしてはいけません！❌

**最終更新**: 2026-03-02 | **実装状況**: ✅ 完全実装

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

## 🔗 PathRegistry 参照 (推奨)

**絶対にハードコードしないこと！** 代わりに `PathRegistry` を使用：

```typescript
import { paths } from './src/system/path_registry.ts';

// ✅ 推奨
const dataPath = paths.dataRoot;              // /mnt/d/investor_all_cached_data/jquants
const cachePath = paths.cacheRoot;            // /mnt/d/investor_all_cached_data/cache
const edinetDb = paths.edinetCacheSqlite;     // /mnt/d/investor_all_cached_data/edinet/cache.sqlite
const memDb = paths.memorySqlite;             // /mnt/d/investor_all_cached_data/cache/memory.sqlite
const outputs = paths.verificationRoot;       // /mnt/d/investor_all_cached_data/outputs
const logs = paths.unifiedLogDir;             // /mnt/d/investor_all_cached_data/logs/unified
```

**使用可能なフィールド一覧**:
```typescript
// Core roots
paths.dataRoot                       // /mnt/d/investor_all_cached_data/jquants
paths.logsRoot                       // /mnt/d/investor_all_cached_data/logs
paths.verificationRoot               // /mnt/d/investor_all_cached_data/outputs
paths.cacheRoot                      // /mnt/d/investor_all_cached_data/cache
paths.edinetRoot                     // /mnt/d/investor_all_cached_data/edinet
paths.preprocessedRoot               // /mnt/d/investor_all_cached_data/preprocessed

// Market data
paths.marketdataRoot                 // /mnt/d/investor_all_cached_data/jquants
paths.marketdataPricesGz             // ...jquants/raw_stock_price.csv.gz
paths.marketdataFinGz                // ...jquants/raw_stock_fin.csv.gz
paths.marketdataListGz               // ...jquants/stock_list.csv.gz
paths.marketdataStatementsDir        // ...jquants/raw_statements

// SQLite caches
paths.marketCacheSqlite              // ...cache/market_cache.sqlite
paths.marketdataSqlite               // ...cache/marketdata.sqlite
paths.httpCacheSqlite                // ...cache/http_cache.sqlite
paths.yahooCacheSqlite               // ...cache/yahoo_finance_cache.sqlite
paths.jquantsPeadCacheSqlite         // ...cache/jquants_pead_cache.sqlite
paths.uqtlSqlite                     // ...cache/uqtl.sqlite
paths.memorySqlite                   // ...cache/memory.sqlite
paths.alphaKnowledgebaseSqlite       // ...cache/alpha_knowledgebase.sqlite

// EDINET
paths.edinetCacheSqlite              // ...edinet/cache.sqlite
paths.edinetSearchSqlite             // ...edinet/search.sqlite
paths.edinetDocsDir                  // ...edinet/docs

// Logs
paths.unifiedLogDir                  // ...logs/unified
```

---

## 🔐 環境変数オーバーライド

ローカル環境やテスト環境で異なるパスを使用する場合は、環境変数でオーバーライド可能：

```bash
export UQTL_DATA_ROOT=/custom/path/to/jquants
export UQTL_LOGS_ROOT=/custom/path/to/logs
export UQTL_VERIFICATION_ROOT=/custom/path/to/outputs
export UQTL_CACHE_ROOT=/custom/path/to/cache
export UQTL_EDINET_ROOT=/custom/path/to/edinet
export UQTL_PREPROCESSED_ROOT=/custom/path/to/preprocessed

# パイプライン実行
task run:newalphasearch
```

---

## 📋 後方互換シンボリックリンク (移行期間)

外部スクリプトの互換性のため、以下のシンボリックリンクが自動作成されます：

| 旧パス | 新パス（実体） |
|---|---|
| `/mnt/d/marketdata` | `→ /mnt/d/investor_all_cached_data/jquants` |
| `logs/cache` | `→ /mnt/d/investor_all_cached_data/cache` |
| `logs/unified` | `→ /mnt/d/investor_all_cached_data/logs/unified` |
| `ts-agent/data` | `→ /mnt/d/investor_all_cached_data/outputs` |

---

## ✅ チェックリスト：新コード追加時

新しいデータアクセスコードを追加する場合は、**必ず**以下をチェック：

- [ ] `PathRegistry` から適切なフィールドを使用している
- [ ] ハードコードされたパスがないか検索: `grep -r "/mnt/d" src/ --include="*.ts"` ❌
- [ ] 相対パスや `process.cwd()` ベースのパス推測がないか確認 ❌
- [ ] `default.yaml` に新しいパスが必要な場合は記載し、`PathRegistry` に追加 ✅
- [ ] テストで異なるパスが必要な場合は環境変数で指定 ✅

---

## 🚀 移行スクリプト参照

全データは以下のスクリプトで `/mnt/d/investor_all_cached_data/` に統合されました：

```bash
bash scripts/migrate_data_to_d_drive.sh
```

**スクリプト内容**:
1. ターゲットディレクトリ作成
2. J-Quants マーケットデータ移行 (rsync)
3. EDINET キャッシュ・ドキュメント移行
4. SQLite キャッシュ移行
5. memory.sqlite 移行
6. 前処理済みデータ移行
7. パイプライン出力移行
8. 監査ログ移行 (unified/experiments/verification)
9. 後方互換シンボリックリンク作成


---

## 📖 関連ドキュメント

- `ts-agent/src/config/default.yaml` — パス設定 (原始値)
- `ts-agent/src/system/path_registry.ts` — PathRegistry 実装
- `CLAUDE.md` — プロジェクト全体の指針
- `docs/diagrams/` — アーキテクチャ図

