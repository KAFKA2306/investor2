# AAARTS Common CLI Design — 詳細仕様

**目的**: AAARTS パイプラインが「手足のように」頻繁に呼ぶ、軽量・高速な CLI ツールチェーン

**設計原則**:
- ✅ 原子的操作（Tier A）
- ✅ チェック系で exit code 活用（Tier B）
- ✅ バッチで並列化（Tier C）
- ✅ 診断は軽量・キャッシュ主体（Tier D）
- ❌ ロギング冗長（--verbose flag で制御）
- ❌ <100ms 応答を目標

---

## Tier A: 単原子操作（原子性重視）

単一のリソース・操作のみ。失敗時は exit 1 でクラッシュ（CDD ルール）。

### A-1. `task data:fetch SYMBOL`
```bash
# 機能: 1 シンボルのマーケットデータ取得
# 実行: J-Quants API → キャッシュに保存
# 出力: JSON { success: bool, symbol: string, records: number, timestamp: ISO8601 }
# exit: 0 (成功), 1 (失敗=クラッシュ)
# 応答: ~5-30s （API 遅延による）

task data:fetch AAPL
# → { "success": true, "symbol": "AAPL", "records": 252, "timestamp": "2026-03-17T10:30:00Z" }
```

### A-2. `task cache:get KEY`
```bash
# 機能: キャッシュ値 1 つ取得（キー指定）
# 実行: SQLite from paths.marketCacheSqlite
# 出力: 値（JSON / CSV / raw string）, または JSON { error: string }
# exit: 0 (キー存在), 1 (キー未検出)
# 応答: <10ms

task cache:get "AAPL:daily:2026-03-17"
# → { "open": 150.5, "close": 151.2, ... }
```

### A-3. `task cache:set KEY VALUE [TTL]`
```bash
# 機能: キャッシュ値 1 つ更新
# 実行: SQLite insert or replace
# 出力: JSON { key: string, ttl?: number, stored_at: ISO8601 }
# exit: 0 (成功), 1 (DB 失敗)
# 応答: <10ms

task cache:set "AAPL:daily:2026-03-17" '{"open":150.5}' 86400
# → { "key": "AAPL:daily:2026-03-17", "ttl": 86400, "stored_at": "2026-03-17T10:30:00Z" }
```

### A-4. `task paths:resolve PATH_KEY`
```bash
# 機能: PathRegistry から 1 パスを解決
# 実行: PathRegistry.get(PATH_KEY)
# 出力: 絶対パス（文字列）or JSON { error: string }
# exit: 0 (解決成功), 1 (キー未検出)
# 応答: <1ms

task paths:resolve "dataRoot"
# → /mnt/d/investor_all_cached_data

task paths:resolve "marketCacheSqlite"
# → /mnt/d/investor_all_cached_data/cache/market_cache.sqlite
```

---

## Tier B: チェック系（結果: exit code / 簡潔 JSON）

**原則**: exit code で分岐、JSON は詳細情報用

### B-1. `task check:cached SYMBOL [FORMAT]`
```bash
# 機能: キャッシュ存在確認
# 出力: exit 0 (存在) / exit 1 (なし), JSON { exists: bool, age_hours?: number, path?: string }
# 応答: <5ms

task check:cached AAPL
# → exit 0
# → { "exists": true, "age_hours": 2, "path": "/mnt/d/.../AAPL.parquet" }

task check:cached UNKNOWN
# → exit 1
# → { "exists": false }
```

### B-2. `task check:fresh SYMBOL HOURS`
```bash
# 機能: N 時間以内の新鮮さ確認
# 出力: exit 0 (十分新鮮) / exit 1 (古い), JSON { fresh: bool, age_hours: number, threshold_hours: number }
# 応答: <5ms

task check:fresh AAPL 24
# → exit 0
# → { "fresh": true, "age_hours": 2, "threshold_hours": 24 }

task check:fresh AAPL 1
# → exit 1
# → { "fresh": false, "age_hours": 2, "threshold_hours": 1 }
```

### B-3. `task check:valid SYMBOL`
```bash
# 機能: スキーマ + データ整合性チェック
# 出力: JSON { valid: bool, errors?: string[], warnings?: string[] }
# exit: 0 (有効) / 1 (無効)
# 応答: <50ms

task check:valid AAPL
# → exit 0
# → { "valid": true, "warnings": [] }

task check:valid BROKEN
# → exit 1
# → { "valid": false, "errors": ["Missing column: close", "NaN in volume"] }
```

### B-4. `task check:schema SYMBOL`
```bash
# 機能: スキーマ定義との一致確認
# 出力: JSON { schema_ok: bool, expected: string[], actual: string[], missing?: string[] }
# exit: 0 (一致) / 1 (不一致)
# 応答: <5ms

task check:schema AAPL
# → exit 0
# → { "schema_ok": true, "expected": ["date", "open", "close", ...], "actual": [...] }
```

---

## Tier C: バッチ系（複数シンボル、並列対応）

**原則**: 複数シンボルの bulk 操作。並列実行対応。部分失敗時は失敗リスト返却。

### C-1. `task fetch:batch SYMBOLS... [--parallel N]`
```bash
# 機能: 複数シンボルを並列取得
# 実行: A-1 (data:fetch) を N 並列実行
# 出力: JSON { succeeded: Symbol[], failed: { symbol: string, error: string }[], total_records: number }
# exit: 0 (全成功) / 1 (一部失敗)
# 応答: ~30s (API 遅延依存)

task fetch:batch AAPL GOOGL MSFT --parallel 3
# → exit 0
# → {
#     "succeeded": ["AAPL", "GOOGL", "MSFT"],
#     "failed": [],
#     "total_records": 756
#   }

task fetch:batch AAPL BROKEN --parallel 2
# → exit 1
# → {
#     "succeeded": ["AAPL"],
#     "failed": [{ "symbol": "BROKEN", "error": "API 404" }],
#     "total_records": 252
#   }
```

### C-2. `task validate:batch SYMBOLS... [--stop-on-error]`
```bash
# 機能: 複数シンボルを検証
# 実行: B-3 (check:valid) を並列実行
# 出力: JSON { valid_symbols: string[], invalid: { symbol: string, errors: string[] }[] }
# exit: 0 (全有効) / 1 (無効あり)
# 応答: <100ms

task validate:batch AAPL GOOGL MSFT
# → exit 0
# → { "valid_symbols": ["AAPL", "GOOGL", "MSFT"], "invalid": [] }

task validate:batch AAPL BROKEN MSFT --stop-on-error
# → exit 1 (即座に停止)
# → { "valid_symbols": ["AAPL"], "invalid": [{ "symbol": "BROKEN", "errors": [...] }] }
```

### C-3. `task cache:warm SYMBOLS... [--ttl SECONDS]`
```bash
# 機能: キャッシュプリロード（複数シンボル）
# 実行: 最新データを fetch してキャッシュ
# 出力: JSON { warmed: string[], skipped: string[], cache_size_mb: number }
# exit: 0 (全プリロード) / 1 (エラー)
# 応答: ~30s

task cache:warm AAPL GOOGL MSFT --ttl 86400
# → exit 0
# → { "warmed": ["AAPL", "GOOGL", "MSFT"], "skipped": [], "cache_size_mb": 15 }
```

### C-4. `task sync:batch SYMBOLS... [--source jquants|edinet|mixseek]`
```bash
# 機能: 複数ソースのデータ同期
# 実行: データソース指定で fetch:batch 実行
# 出力: JSON { source: string, synced: Symbol[], failed: Symbol[] }
# exit: 0 / 1
# 応答: ~60s (複数 API)

task sync:batch AAPL GOOGL --source jquants
# → { "source": "jquants", "synced": ["AAPL", "GOOGL"], "failed": [] }
```

---

## Tier D: 診断系（軽量、キャッシュ主体）

**原則**: **実行時間 <100ms** を目標。キャッシュからの読み込みのみ。

### D-1. `task stat:one SYMBOL [--format json|csv|table]`
```bash
# 機能: 1 シンボルの簡易統計
# 実行: キャッシュから読み込み、計算（秒単位）
# 出力: JSON { symbol: string, records: number, date_range: [from, to], nan_count: number }
# exit: 0 (成功) / 1 (キャッシュ未検出)
# 応答: <10ms

task stat:one AAPL --format json
# → {
#     "symbol": "AAPL",
#     "records": 252,
#     "date_range": ["2025-03-17", "2026-03-17"],
#     "nan_count": 0
#   }
```

### D-2. `task stat:all [--format json|csv]`
```bash
# 機能: 全シンボル統計
# 実行: キャッシュメタデータ集約
# 出力: JSON array or CSV
# exit: 0
# 応答: <50ms

task stat:all --format json
# → [
#     { "symbol": "AAPL", "records": 252, "cache_age_hours": 2 },
#     { "symbol": "GOOGL", "records": 252, "cache_age_hours": 5 },
#     ...
#   ]
```

### D-3. `task log:tail [N] [--filter PATTERN]`
```bash
# 機能: 最新 N 行ログ表示
# 実行: paths.unifiedLogDir から tail
# 出力: 行単位（テキスト）or JSON array
# exit: 0
# 応答: <10ms

task log:tail 20
# → [last 20 lines]

task log:tail 50 --filter "ERROR"
# → [last 50 lines with ERROR]
```

### D-4. `task health:check [--detailed]`
```bash
# 機能: パイプライン全体の軽量ヘルスチェック
# 実行: PathRegistry, キャッシュ, ログ の簡易確認
# 出力: JSON { healthy: bool, checks: { name: string, status: bool }[] }
# exit: 0 (健全) / 1 (問題あり)
# 応答: <20ms

task health:check
# → {
#     "healthy": true,
#     "checks": [
#       { "name": "PathRegistry", "status": true },
#       { "name": "CacheSqlite", "status": true },
#       { "name": "LogDir", "status": true }
#     ]
#   }
```

---

## 実装例（Taskfile.yml スニペット）

```yaml
version: '3'

tasks:
  # Tier A
  data:fetch:
    desc: "Fetch 1 symbol from J-Quants"
    cmd: bun run src/commands/data_fetch.ts {{.SYMBOL}}
    requires:
      vars: [SYMBOL]

  cache:get:
    desc: "Get 1 cache value by key"
    cmd: bun run src/commands/cache_get.ts {{.KEY}}
    requires:
      vars: [KEY]

  # Tier B
  check:cached:
    desc: "Check if symbol is cached"
    cmd: bun run src/commands/check_cached.ts {{.SYMBOL}}
    requires:
      vars: [SYMBOL]

  check:fresh:
    desc: "Check if data is fresh (within N hours)"
    cmd: bun run src/commands/check_fresh.ts {{.SYMBOL}} {{.HOURS}}
    requires:
      vars: [SYMBOL, HOURS]

  # Tier C
  fetch:batch:
    desc: "Fetch multiple symbols in parallel"
    cmd: bun run src/commands/fetch_batch.ts {{.SYMBOLS}} --parallel {{.PARALLEL | default "3"}}
    requires:
      vars: [SYMBOLS]

  # Tier D
  stat:one:
    desc: "Show stats for 1 symbol (from cache)"
    cmd: bun run src/commands/stat_one.ts {{.SYMBOL}}
    requires:
      vars: [SYMBOL]

  health:check:
    desc: "Lightweight health check"
    cmd: bun run src/commands/health_check.ts
```

---

## 使用パターン（パイプラインコード内）

```typescript
// Example: Pipeline が 100 シンボルを処理する場合

// 1. 事前チェック
const health = JSON.parse(exec('task health:check'));
if (!health.healthy) throw new Error('Pipeline unhealthy');

// 2. バッチ取得 + 検証
const batch = JSON.parse(
  exec('task fetch:batch', symbols, '--parallel 5')
);
if (batch.failed.length > 0) {
  throw new Error(`Failed symbols: ${batch.failed.map(f => f.symbol)}`);
}

// 3. 1 つずつ処理
for (const symbol of batch.succeeded) {
  // 鮮度確認
  const fresh = exec('task check:fresh', [symbol, '24']) === 0;
  if (!fresh) continue; // スキップ

  // 有効性確認
  const valid = exec('task check:valid', [symbol]) === 0;
  if (!valid) continue;

  // 実処理
  processSymbol(symbol);
}

// 4. 診断
const stats = JSON.parse(exec('task stat:all --format json'));
log(`Processed: ${stats.length} symbols`);
```

---

## まとめ表

| Tier | 特性 | 呼出頻度 | 応答 | exit code 活用 |
|------|------|--------|------|----------------|
| **A** | 単原子 | 高（毎シンボル） | ~5-30s | 少ない |
| **B** | チェック | 高（条件分岐） | <50ms | 頻繁 |
| **C** | バッチ | 中（初期化時） | ~30s | 中程度 |
| **D** | 診断 | 低（監視・デバッグ） | <50ms | なし |
