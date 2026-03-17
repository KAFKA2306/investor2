# スキーマ統合検証チェックリスト
**対象**: 7 ファイル分散スキーマ → src/schemas.ts 統合
**基準**: CLAUDE.md Unified Schemas ルール（p.71-136）
**準備日**: 2026-03-17

---

## 📊 分散スキーママッピング表

| # | 現在のファイル | スキーマ数 | 主要スキーマ | ドメイン | 統合後の位置 |
|---|---------------|----------|-----------|--------|-----------|
| 1 | `schemas_polymarket_schemas.ts` | 17 | Token, Orderbook, Market, Signal, Trade, Position, Event | Polymarket | `src/schemas.ts` / Polymarket Trading |
| 2 | `schemas_allocation_schema.ts` | 3 | InvestmentIdea, AllocationRequest, AllocationResult | Allocation | `src/schemas.ts` / Allocation & Investment |
| 3 | `schemas_alpha_quality_optimizer_schema.ts` | 6 | MarketSnapshot, PlaybookPattern, AlphaQualityOptimizer (Input/Output/Config) | Alpha Quality | `src/schemas.ts` / Alpha Quality |
| 4 | `schemas_financial_domain_schemas.ts` | 48 | EdinetDocument, Event, YahooChart, OHLC, FinanceSnapshot, AlphaFactors, Metrics, AcePlaybook, StrategicReasoning, AlphaScreening, VerificationPerformance, UnifiedLog, etc. | Multi-Domain | `src/schemas.ts` / Financial Domain (複数サブグループ) |
| 5 | `schemas_alpha_consistency_schema.ts` | ? | AlphaConsistency (推定) | Alpha Consistency | `src/schemas.ts` / Alpha Validation |
| 6 | `schemas_tenbagger_schema.ts` | 2 | TenbaggerMetrics, TenbaggerCandidate | Tenbagger | `src/schemas.ts` / Investment Ideas |
| 7 | `schemas_edinet_io_contract_schema.ts` | 5 | EdinetIoViolationCategory, EdinetIoViolationCode, EdinetIoViolation, EdinetIoReport, EdinetIoRepairReport | EDINET I/O | `src/schemas.ts` / EDINET |

**推定スキーマ総数**: 81 個（統合対象）

---

## ✅ 統合チェックリスト

### PHASE 1: Import 置換（影響範囲特定）

**ステップ 1.1: Import 検索（pre-migration）**

```bash
# 現在の分散スキーマ import を全検出
grep -r "from.*schemas_" src --include="*.ts" | tee /tmp/schema_imports_pre.txt

# ファイル数カウント
cat /tmp/schema_imports_pre.txt | cut -d: -f1 | sort -u | wc -l

# リスト表示
cat /tmp/schema_imports_pre.txt | cut -d: -f1 | sort -u
```

**期待値**: 30-50 ファイルが分散スキーマから import

**チェックボックス**:
- [ ] import 検索実行完了
- [ ] 影響ファイル数記録
- [ ] 7 ファイルすべてで import 検出

---

### PHASE 2: スキーマ集約（src/schemas.ts 再構成）

**ステップ 2.1: src/schemas.ts のドメイン別グループ化構造**

統合後の推奨構成：

```typescript
// ============================================
// 📦 src/schemas.ts - Unified Schema Source
// ============================================

// 1. Polymarket Trading (17 schemas)
export const TokenSchema = z.object({ ... });
export const OrderbookSchema = z.object({ ... });
export const MarketSchema = z.object({ ... });
export const SignalSchema = z.object({ ... });
export const PolymarketTradeSchema = z.object({ ... });
export const PolymarketPositionSchema = z.object({ ... });
export const PolymarketEventSchema = z.object({ ... });
// ... (10+ more)

// 2. Allocation & Investment (3 + 2 = 5 schemas)
export const InvestmentIdeaSchema = z.object({ ... });
export const AllocationRequestSchema = z.object({ ... });
export const AllocationResultSchema = z.object({ ... });
export const TenbaggerMetricsSchema = z.object({ ... });
export const TenbaggerCandidateSchema = z.object({ ... });

// 3. Alpha Quality & Screening (6 + validation = 7+)
export const AlphaQualityOptimizerInputSchema = z.object({ ... });
export const AlphaQualityOptimizerOutputSchema = z.object({ ... });
export const AlphaQualityOptimizerConfigSchema = z.object({ ... });
export const AlphaScreeningSchema = z.object({ ... });
export const AlphaSignificanceSchema = z.object({ ... });
export const MarketSnapshotSchema = z.object({ ... });
export const PlaybookPatternSchema = z.object({ ... });

// 4. Financial Domain (48+ schemas)
// 4a. EDINET & Documentation
export const EdinetDocumentSchema = z.object({ ... });
export const EdinetDocumentListResponseSchema = z.object({ ... });

// 4b. Market Data
export const YahooChartSchema = z.object({ ... });
export const Ohlc6Schema = z.object({ ... });
export const FinanceSnapshotSchema = z.object({ ... });
export const DailyQuoteSchema = z.object({ ... });

// 4c. Alpha & Factors
export const AlphaFactorsSchema = z.object({ ... });
export const MetricsSchema = z.object({ ... });

// 4d. Strategic Analysis
export const AcePlaybookSchema = z.object({ ... });
export const StrategicReasoningSchema = z.object({ ... });

// 4e. Verification & Audit
export const VerificationPerformanceSchema = z.object({ ... });
export const ExecutionAuditSchema = z.object({ ... });
export const StandardOutcomeSchema = z.object({ ... });

// 4f. Logging & Reporting
export const UnifiedLogSchema = z.object({ ... });
export const BenchmarkReportSchema = z.object({ ... });
export const CycleSummarySchema = z.object({ ... });

// ... (remaining schemas grouped by domain)

// 5. EDINET I/O Contract (5 schemas)
export const EdinetIoViolationSchema = z.object({ ... });
export const EdinetIoReportSchema = z.object({ ... });
export const EdinetIoRepairReportSchema = z.object({ ... });

// 6. Events & Messages (1+ schemas)
export const EventTypeSchema = z.enum([...]);
export const BaseEventSchema = z.object({ ... });

// ============================================
// Type Inference (Rule 2)
// ============================================
export type Token = z.infer<typeof TokenSchema>;
export type Market = z.infer<typeof MarketSchema>;
// ... (all 81 types)

// ============================================
// Validation Functions (if needed)
// ============================================
export function validateQlibFormula(formula: string): boolean { ... }
// ... (shared validators)
```

**チェックボックス**:
- [ ] ドメイン別グループ構造を src/schemas.ts に作成
- [ ] 全 81 スキーマ コピーペースト完了
- [ ] z.infer<typeof> 型推論適用（全スキーマ）
- [ ] スキーマ依存関係（例: PolymarketTradeSchema が Signal 参照）を解決

---

### PHASE 3: Import パス置換（リファクタリング）

**ステップ 3.1: 置換戦略**

各影響ファイルに対して以下を実行：

```typescript
// Before:
import { MarketSchema, type Market } from "../../schemas/polymarket_schemas";

// After:
import { MarketSchema, type Market } from "../schemas";
```

**置換パターン（正規表現）**:

| パターン | 置換先 | 例 |
|---------|-------|-----|
| `from ".*schemas_polymarket_schemas"` | `from "../schemas"` | `../schemas_polymarket_schemas` |
| `from ".*schemas_allocation_schema"` | `from "../schemas"` | `./schemas_allocation_schema` |
| `from ".*schemas_alpha_quality_optimizer_schema"` | `from "../schemas"` | `../../schemas_alpha_quality_optimizer_schema` |
| `from ".*schemas_financial_domain_schemas"` | `from "../schemas"` | `../schemas_financial_domain_schemas` |
| `from ".*schemas_alpha_consistency_schema"` | `from "../schemas"` | `./schemas_alpha_consistency_schema` |
| `from ".*schemas_tenbagger_schema"` | `from "../schemas"` | `../schemas_tenbagger_schema` |
| `from ".*schemas_edinet_io_contract_schema"` | `from "../schemas"` | `./schemas_edinet_io_contract_schema` |

**実行順序（依存関係）**:
1. **財務ドメイン** (schemas_financial_domain_schemas.ts) → 多くのファイルが依存
2. **Polymarket** (schemas_polymarket_schemas.ts) → ポリマーケット機能が依存
3. **Alpha Quality** (schemas_alpha_quality_optimizer_schema.ts) → 品質チェック依存
4. **その他** (allocation, consistency, tenbagger, edinet)

**チェックボックス**:
- [ ] sed/ripgrep スクリプト作成（置換コマンド）
- [ ] 影響ファイル 30-50 個に置換実行
- [ ] 置換後の import パス検証（エラーなし）
- [ ] 重複 import なし（同一スキーマ 2 回以上なし）

---

### PHASE 4: 型推論検証（Rule 2）

**ステップ 4.1: z.infer<typeof> 確認**

```bash
# src/schemas.ts で z.infer<typeof> 使用率
grep -c "z.infer" src/schemas.ts

# 期待値: 81 行以上（全スキーマの type 定義）
```

**チェックボックス**:
- [ ] 全 81 スキーマで `export type XxxSchema = z.infer<typeof XxxSchema>` を定義
- [ ] 型推論で別途 interface/type 定義なし（CLAUDE.md Rule 2 順守）
- [ ] TypeScript 型チェック成功：`yarn tsc --noEmit`

---

### PHASE 5: スキーマ依存関係解決

**ステップ 5.1: 内部参照チェック**

```bash
# 各スキーマ内で他のスキーマを参照しているか検出
grep -o "Schema\|type " src/schemas_*.ts | grep -v "^export" | sort | uniq -c | sort -rn
```

**期待される依存関係例**:
- `PolymarketTradeSchema` → `SignalSchema` 参照？
- `AlphaQualityOptimizerOutputSchema` → `MarketSnapshotSchema` 参照？
- `UnifiedLogSchema` → 多数の sub-schema 参照

**チェックボックス**:
- [ ] 依存グラフ作成（ドメイン内での参照関係）
- [ ] 循環参照なし（A → B → A パターンなし）
- [ ] 外部参照（z.lazy など）明記

---

### PHASE 6: 検証コマンド一覧

#### 6a. Lint & Format

```bash
# Biome チェック
biome check --config config/biome.json src/schemas.ts

# 修正
biome format --config config/biome.json src/schemas.ts --write
```

**チェックボックス**:
- [ ] Biome チェック合格
- [ ] `no any` ルール準守（TS strict）
- [ ] 命名規則順守（Schema + PascalCase）

#### 6b. TypeScript 型チェック

```bash
# 全体型チェック
yarn tsc --noEmit

# src/schemas.ts 単独チェック
yarn tsc --noEmit src/schemas.ts

# 推奨: strict モード
yarn tsc --strict --noEmit src/schemas.ts
```

**チェックボックス**:
- [ ] エラー 0 個
- [ ] 警告 0 個
- [ ] strict モード準守

#### 6c. Import パス検証

```bash
# 分散スキーマへの残り import 検出（SHOULD BE ZERO）
grep -r "from.*schemas_polymarket_schemas\|from.*schemas_allocation_schema\|from.*schemas_financial_domain\|from.*schemas_alpha_consistency\|from.*schemas_tenbagger\|from.*schemas_edinet_io_contract\|from.*schemas_alpha_quality_optimizer" src --include="*.ts" | wc -l

# 期待値: 0
```

**チェックボックス**:
- [ ] 分散スキーマへの import 0 個
- [ ] 全 import が `from "../schemas"` または `from "../../schemas"`
- [ ] 相対パス正しい（import 元ファイルからの距離）

#### 6d. エクスポート確認

```bash
# src/schemas.ts で定義されたスキーマ総数
grep "^export const.*Schema" src/schemas.ts | wc -l

# 期待値: 81 以上
```

**チェックボックス**:
- [ ] 81 スキーマすべてが `export const` で公開
- [ ] Type も `export type` で公開
- [ ] Enum, Validator 関数も export

#### 6e. 実行時検証（Optional）

```bash
# Node/Bun で import テスト
node --input-type=module -e "import { MarketSchema, InvestmentIdeaSchema } from './src/schemas.ts'; console.log('Import OK')"

# または Bun
bun -e "import { MarketSchema } from './src/schemas.ts'; console.log('Import OK')"
```

**チェックボックス**:
- [ ] 実行時エラーなし
- [ ] Circular dependency なし

---

## 🔧 リファクタリング優先順（依存度順）

```
HIGH PRIORITY (多くのファイルが依存):
1. schemas_financial_domain_schemas.ts       (48+ schemas, 広範な依存)
2. schemas_polymarket_schemas.ts             (17 schemas, Polymarket 機能)
3. schemas_alpha_quality_optimizer_schema.ts (6 schemas, 品質チェック)

MEDIUM PRIORITY:
4. schemas_allocation_schema.ts              (3 schemas, アロケーション)
5. schemas_edinet_io_contract_schema.ts      (5 schemas, EDINET I/O)

LOW PRIORITY (局所的):
6. schemas_tenbagger_schema.ts               (2 schemas, 特定機能)
7. schemas_alpha_consistency_schema.ts       (? schemas, 特定バリデーション)
```

---

## 📋 完了基準（GO/NO-GO）

### GO（統合成功）
- ✅ PHASE 1-6 全チェックボックス完了
- ✅ Biome lint エラー 0 個
- ✅ TypeScript 型チェック エラー 0 個
- ✅ 分散スキーマへの import 0 個
- ✅ 81 スキーマすべて src/schemas.ts に存在・export 確認
- ✅ 実行時エラーなし

### HOLD（追加検証必要）
- ⚠️ 1-2 個の型チェック警告 → 解決可能な範囲
- ⚠️ 1-2 個の lint 警告 → 除外ルール追加検討

### NO-GO（ロールバック）
- ❌ TypeScript 型チェック エラー 3 個以上
- ❌ 分散スキーマへの import 5 個以上残存
- ❌ Circular dependency 検出
- ❌ 実行時 crash

---

## 📌 推奨進行方法

### 日程（並列処理）
```
T+0:   PHASE 1.1 (import 検索)
       ↓
T+0.5: PHASE 2.1 (src/schemas.ts 再構成) 開始
       並列: ドメイン別グループ作業分担
       ↓
T+2:   PHASE 3.1 (import 置換) 開始
       優先度順に sed/ripgrep スクリプト実行
       ↓
T+3:   PHASE 4 + 5 (型検証・依存関係)
       ↓
T+4:   PHASE 6 (検証コマンド実行)
       ↓
T+5:   GO/NO-GO 判定
```

### 作業分担（推奨）
- **Person A**: PHASE 2.1（financial_domain スキーマ集約）
- **Person B**: PHASE 2.1（polymarket + allocation スキーマ）
- **Person C**: PHASE 3.1（import 置換スクリプト）
- **Person D**: PHASE 4-6（型検証・検証コマンド）

---

## 🎯 成功指標

| メトリクス | 目標 | 現在 | GO 時 |
|----------|------|------|------|
| 統合スキーマ数 | 81+ | 81 | ✅ 81 |
| import パス | 1 個（src/schemas） | 7 個 | ✅ 1 |
| Lint エラー | 0 | ? | ✅ 0 |
| 型チェック エラー | 0 | ? | ✅ 0 |
| 実行時エラー | 0 | ? | ✅ 0 |
| 循環参照 | 0 | ? | ✅ 0 |

---

## 📎 附属資料

**参照**: CLAUDE.md p.71-136 (Unified Schemas ルール)
**基準**: CDD (Crash-Driven Development) — エラーは propagate

---

**検証チェックリスト作成者**: Claude Haiku 4.5
**監査レポート基準**: CURRENT_STATE_AUDIT.md
**実装ターゲット**: Task #13（スキーマ統合実装）
