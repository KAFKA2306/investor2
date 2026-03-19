# Task #7: Data Expansion (J-Quants 2020-2025)

## 概要
J-Quants キャッシュを3ヶ月分（2024-01-03～2024-03-30）から6年間分（2020-01-01～2025-12-31）に拡張する。

## 実施内容

### 1. スクリプト修正: src/io/get.ts

#### 変更前（730日制限）
```typescript
const now = new Date();
const to = now.toISOString().split("T")[0];
const backfillDays = mode === "markets" ? 730 : 365;
const from = new Date(now.getTime() - backfillDays * 24 * 60 * 60 * 1000)
  .toISOString()
  .split("T")[0];
```

#### 変更後（6年間固定）
```typescript
const from = "2020-01-01";
const to = "2025-12-31";
```

### 2. 日付生成ロジック更新

#### 新規 getDateRange 関数
```typescript
function getDateRange(fromStr: string, toStr: string): string[] {
  const dates: string[] = [];
  const current = new Date(fromStr);
  const end = new Date(toStr);
  while (current <= end) {
    dates.push(current.toISOString().split("T")[0]);
    current.setDate(current.getDate() + 1);
  }
  return dates;
}
```

対象日数：2020-01-01～2025-12-31 = 約 2,190日（6年間）

### 3. 実行コマンド

```bash
cd /home/kafka/finance/investor2
export JQUANTS_API_KEY="<api_key>"
GET_MODE=jquants bun src/io/get.ts
```

このコマンドで以下をフェッチ：
- **マーケットデータ**: equities/bars/daily + indices/bars/daily/topix（730 API呼び出し×2）
- **基本データ**: fins/summary（730 API呼び出し）
- **マスターデータ**: equities/master（1 API呼び出し）

## 実行時間見積もり

- レート制限: 500ms/リクエスト（~2 req/sec）
- 総リクエスト数: 730 × 2 + 730 + 1 = 2,191
- 予想実行時間: 約 18分～1時間

## キャッシュ保存先

データはSQLiteキャッシュに保存される：
```
config.paths.cacheMarketsJquants
```

## 次ステップ

1. データ同期実行完了後、cache/sector_spillover/sector_returns.db を確認
2. セクタースピルオーバーバックテストを実行：
   ```bash
   bun src/commands/sector_spillover_backtest.ts
   ```
3. 3ヶ月版と6年版の結果比較

## 注記

- CDD原則に従い、エラーは伝播させる（try-catchなし）
- APIレート制限に違反しないよう500ms待機を挿入
- キャッシュは http_cache テーブルに保存され、重複リクエストはスキップ
