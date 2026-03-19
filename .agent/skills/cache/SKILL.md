---
name: cache
description: |
  **When to use:** All data fetching operations, caching decisions, avoiding redundant API calls.
  **Pushy:** Enforce cache-first pattern. Promote data reuse from existing cache instead of API calls.
  Trigger phrases: cached data, cache data, reuse data, avoid API call, HTTP cache, data cache, fetch from cache
---

# キャッシュデータを使いこなそう！🎀

## 💡 Core Principle: Cache-First is MANDATORY

キャッシュはただのパフォーマンス最適化ではない。**存在するデータを再利用する**のは当たり前のエチケットなのだ！✨

API を叩く前に、まずキャッシュを確認。既に取得済みのデータがあるなら、それを使い回すのだ。無駄な API 呼び出しは避けるべし。

---

## 📍 Where Caches Live (SSOT: config/default.yaml)

全キャッシュ設定は `config/default.yaml` の `paths` セクションに集約されている。使う時は **PathRegistry** から取得するのだ。

### Logical Cache Organization

```yaml
# Market Data (Real-time prices, quotes)
cacheMarketsPolymarket:     /mnt/d/.../cache/markets/polymarket.sqlite
cacheMarketsJquants:        /mnt/d/.../cache/markets/jquants.sqlite
cacheMarketsYahoo:          /mnt/d/.../cache/markets/yahoo.sqlite

# Fundamental Data (Financial statements, ratios)
cacheFundamentalJquants:    /mnt/d/.../cache/fundamental/jquants_fin.sqlite
cacheFundamentalEdinet:     /mnt/d/.../cache/fundamental/edinet.sqlite

# Macro Data (GDP, inflation, rates)
cacheMacroEstat:            /mnt/d/.../cache/macro/estat.sqlite
cacheMacroFred:             /mnt/d/.../cache/macro/fred.sqlite

# HTTP Response Cache (J-Quants API payloads)
cacheMarketsJquants:        /mnt/d/.../cache/markets/jquants.sqlite
```

---

## 🔍 How to Read from Cache (Pattern)

### Example: J-Quants Market Data

```typescript
import { Database } from "bun:sqlite";
import { config } from "../commands/_config.ts";

const jquantsDb = new Database(config.paths.cacheMarketsJquants);

// Query cached equities master data
const masterCacheRows = jquantsDb
  .query("SELECT value FROM http_cache WHERE key LIKE '%/equities/master%'")
  .all() as Array<{ value: string }>;

if (masterCacheRows.length === 0) {
  throw new Error("J-Quants master data not in cache. Run `task data:sync` first.");
}

const masterData = JSON.parse(masterCacheRows[0].value);
```

**Key Pattern**:
1. ✅ Open database using config path
2. ✅ Query by `http_cache` table
3. ✅ Parse JSON response
4. ✅ THROW error if missing (never silent fallback)

---

## ⚠️ Mistakes to Avoid

### ❌ Mistake 1: Hardcoded Cache Paths

```typescript
// WRONG
const db = new Database("/mnt/d/investor_all_cached_data/cache/markets/jquants.sqlite");
```

```typescript
// CORRECT
import { config } from "../commands/_config.ts";
const db = new Database(config.paths.cacheMarketsJquants);
```

### ❌ Mistake 2: Defensive Fallbacks

```typescript
// WRONG - hides real issues
const cached = getCachedReturns(fromDate, toDate);
if (cached.length === 0) {
  return []; // Silently returns empty instead of alerting
}
```

```typescript
// CORRECT - let errors propagate
if (codeToSector.size === 0) {
  return []; // Only for expected empty states
}

if (masterCacheRows.length === 0) {
  throw new Error("Master data not cached"); // Unexpected state = crash
}
```

### ❌ Mistake 3: Reloading Configuration

```typescript
// WRONG - duplicates config parsing
import yaml from "js-yaml";
import { readFileSync } from "node:fs";
const config = ConfigSchema.parse(
  yaml.load(readFileSync("config/default.yaml", "utf-8"))
);
```

```typescript
// CORRECT - import once
import { config } from "../commands/_config.ts";
```

---

## 🚀 Cache Management (Operations)

### Data Sync

キャッシュを最新に保つ：

```bash
task data:sync
```

すべての外部データソース（J-Quants, EDINET, Yahoo Finance）から最新データを取得し、キャッシュに保存するのだ。

### Check Cache Health

キャッシュの状態を確認：

```bash
task cache:inspect
```

---

## 📊 Common Cache Queries

### J-Quants Master Data (株コード → セクターコード)

```typescript
const masterCacheRows = jquantsDb
  .query("SELECT value FROM http_cache WHERE key LIKE '%/equities/master%'")
  .all() as Array<{ value: string }>;

const masterData = JSON.parse(masterCacheRows[0].value);
for (const stock of masterData.data || []) {
  codeToSector.set(stock.Code, String(Number(stock.S17) * 1000));
}
```

### J-Quants Daily Bars (日次OHLCV)

```typescript
const barCacheRows = jquantsDb
  .query(
    "SELECT key, value FROM http_cache WHERE key LIKE '%/equities/bars/daily%' ORDER BY key DESC LIMIT 500"
  )
  .all() as Array<{ key: string; value: string }>;

for (const row of barCacheRows) {
  const data = JSON.parse(row.value);
  for (const bar of data.data || []) {
    // Process bar data (Code, Date, Close, etc.)
  }
}
```

---

## 💡 Decision Tree: Cache vs. API

```
Does this data already exist in cache?
  ├─ YES → Use cached data (getFromCache())
  └─ NO → Fetch from API, then cache (fetchAndCache())

Is the cached data fresh enough?
  ├─ YES (< configured TTL) → Use as-is
  └─ NO (stale) → Run `task data:sync` and try again

Should this data EVER be regenerated?
  ├─ NO (historical/immutable) → Cache forever
  └─ YES (daily updates) → Trigger sync via Taskfile
```

---

## 🎯 Checklist: Before Fetching

- [ ] Is there a config path for this cache? (Check `config/default.yaml`)
- [ ] Does the cache file exist? (If not, run `task data:sync`)
- [ ] What's the table structure? (`http_cache`, `sector_returns`, custom table?)
- [ ] What's the query key pattern? (LIKE '%/equities/master%', etc.)
- [ ] If empty, should I throw or return empty? (Throw = unexpected, empty = expected)
- [ ] Are config values hardcoded? (Use `config.paths.*` instead)

---

## 📚 Related Files

- `src/io/sector_data_fetcher.ts` — J-Quants cache query example
- `src/commands/_config.ts` — Config loader (import this, don't reload YAML)
- `config/default.yaml` — Cache path SSOT
- `docs/DATA_STRUCTURE.md` — Unified data architecture

