# Schema Unification Strategy — src/schemas.ts Single SSOT

**Date**: 2026-03-17
**Status**: Design Complete, Ready for Implementation (Task #13)
**Target**: Consolidate all type definitions into `src/schemas.ts`

---

## 1. Current Schema Landscape

### 1.1 Distribution Map

Currently, type definitions are scattered across **7 files**. Only 1 file (`src/shared/schema.ts`) uses Zod; the rest use plain TypeScript `interface` declarations.

| # | File | Schemas/Types | Zod? | Domain |
|---|------|--------------|------|--------|
| 1 | `src/shared/schema.ts` | `ConfigSchema`, `Config` | Yes | Configuration |
| 2 | `src/preprocess/screener.ts` | `StockRecord`, `StockListRow`, `FinRow` | No | Market Data |
| 3 | `src/preprocess/edinet.ts` | `StockListEntry`, `RawFinancialRecord`, `CompanyInfo`, `CompanyGovernance`, `FinancialData`, `CompanyDetail` | No | EDINET / Fundamentals |
| 4 | `src/preprocess/text.ts` | `XBRLText` | No | XBRL Text |
| 5 | `src/dashboard/server.ts` | `CacheStatistics` | No | Dashboard / Stats |
| 6 | `src/tasks/stats.ts` | `CacheStatistics` (duplicate) | No | CLI Stats |
| 7 | `src/commands/health_check.ts` | `Check` | No | Health Check |

### 1.2 Inventory Summary

| Category | Count |
|----------|-------|
| Zod schemas | 1 (`ConfigSchema`) |
| Plain interfaces | 12 unique (+ 1 duplicate `CacheStatistics`) |
| Exported interfaces | 4 (`CompanyInfo`, `CompanyGovernance`, `FinancialData`, `CompanyDetail`) |
| File-local interfaces | 9 |
| Total type definitions | 13 unique |

### 1.3 Cross-File Dependencies

```
src/shared/schema.ts (ConfigSchema)
  ← imported by: 11 files (all commands/, io/get.ts, preprocess/*, dashboard/server.ts, tasks/stats.ts)

src/preprocess/edinet.ts (CompanyInfo, CompanyGovernance, FinancialData, CompanyDetail)
  ← imported by: src/dashboard/server.ts (via function imports: getCompanyDetail, searchCompanies, etc.)

src/preprocess/screener.ts (StockRecord — NOT exported as type, only via getScreenerData())
  ← imported by: src/dashboard/server.ts (via getScreenerData function)
```

### 1.4 Duplicate Detection

`CacheStatistics` is defined identically in both:
- `src/dashboard/server.ts:21-41`
- `src/tasks/stats.ts:10-30`

This is an active SSOT violation.

---

## 2. Target Architecture

### 2.1 File: `src/schemas.ts`

```typescript
import { z } from "zod";

// ============================================================
// Configuration
// ============================================================
export const ConfigSchema = z.object({ ... });
export type Config = z.infer<typeof ConfigSchema>;

// ============================================================
// Market Data (Screener)
// ============================================================
export const StockRecordSchema = z.object({ ... });
export type StockRecord = z.infer<typeof StockRecordSchema>;

export const StockListRowSchema = z.object({ ... });
export type StockListRow = z.infer<typeof StockListRowSchema>;

export const FinRowSchema = z.object({ ... });
export type FinRow = z.infer<typeof FinRowSchema>;

// ============================================================
// EDINET / Fundamentals
// ============================================================
export const StockListEntrySchema = z.object({ ... });
export type StockListEntry = z.infer<typeof StockListEntrySchema>;

export const RawFinancialRecordSchema = z.object({ ... });
export type RawFinancialRecord = z.infer<typeof RawFinancialRecordSchema>;

export const CompanyInfoSchema = z.object({ ... });
export type CompanyInfo = z.infer<typeof CompanyInfoSchema>;

export const CompanyGovernanceSchema = z.object({ ... });
export type CompanyGovernance = z.infer<typeof CompanyGovernanceSchema>;

export const FinancialDataSchema = z.object({ ... });
export type FinancialData = z.infer<typeof FinancialDataSchema>;

export const CompanyDetailSchema = z.object({ ... });
export type CompanyDetail = z.infer<typeof CompanyDetailSchema>;

// ============================================================
// XBRL Text
// ============================================================
export const XBRLTextSchema = z.object({ ... });
export type XBRLText = z.infer<typeof XBRLTextSchema>;

// ============================================================
// Cache & Statistics
// ============================================================
export const CacheStatisticsSchema = z.object({ ... });
export type CacheStatistics = z.infer<typeof CacheStatisticsSchema>;

// ============================================================
// Health Check
// ============================================================
export const CheckSchema = z.object({ ... });
export type Check = z.infer<typeof CheckSchema>;
```

### 2.2 Design Decisions

1. **All interfaces become Zod schemas** — enables runtime validation at system boundaries (CDD alignment: crash on bad data, not silently accept)
2. **Types derived via `z.infer<typeof>`** — never duplicate interface definitions
3. **File-local interfaces promoted to shared** — even `Check` and `FinRow`, which are currently local, benefit from centralization to prevent future drift
4. **`src/shared/schema.ts` is deleted** — replaced entirely by `src/schemas.ts`
5. **Import path**: `from "../schemas"` (not `from "../shared/schema"`)

---

## 3. Migration Plan

### Phase 1: Non-Breaking Foundation (1 hour)

**Goal**: Create `src/schemas.ts` with all schemas, keeping old files intact.

1. Create `src/schemas.ts`
2. Move `ConfigSchema` + `Config` from `src/shared/schema.ts`
3. Convert all plain interfaces to Zod schemas:
   - `StockRecord`, `StockListRow`, `FinRow` (from screener.ts)
   - `StockListEntry`, `RawFinancialRecord`, `CompanyInfo`, `CompanyGovernance`, `FinancialData`, `CompanyDetail` (from edinet.ts)
   - `XBRLText` (from text.ts)
   - `CacheStatistics` (from server.ts / stats.ts — deduplicate)
   - `Check` (from health_check.ts)
4. Re-export from `src/shared/schema.ts` for backward compatibility:
   ```typescript
   export { ConfigSchema, type Config } from "../schemas";
   ```
5. Run `bun x tsc --noEmit` — must pass with zero errors

### Phase 2: Import Replacement (2 hours)

**Goal**: Update all import statements to point to `src/schemas.ts`.

1. Replace all `import { ConfigSchema } from "../shared/schema"` with `import { ConfigSchema } from "../schemas"`
2. Replace all local interface usages with imports from `src/schemas.ts`
3. Remove duplicate `CacheStatistics` from `server.ts` and `stats.ts`
4. Remove local interface definitions from `screener.ts`, `edinet.ts`, `text.ts`, `health_check.ts`
5. Run `bun x tsc --noEmit` after each file modification

### Phase 3: Cleanup (30 min)

**Goal**: Remove backward-compatibility shims and verify.

1. Delete `src/shared/schema.ts` (all consumers now import from `src/schemas.ts`)
2. Verify no remaining imports from `shared/schema`:
   ```bash
   grep -r "from.*shared/schema" src/ --include="*.ts"
   ```
   Expected: 0 results
3. Final `bun x tsc --noEmit`
4. Run `bun run src/dashboard/server.ts` smoke test

---

## 4. Import Replacement Strategy

### 4.1 Before / After Examples

```typescript
// BEFORE: ConfigSchema from shared/schema
import { ConfigSchema } from "../shared/schema";
// AFTER:
import { ConfigSchema } from "../schemas";

// BEFORE: Exported interfaces from edinet.ts
import { CompanyInfo, CompanyDetail } from "../preprocess/edinet";
// AFTER: (these are imported via function, not type — see 4.3)

// BEFORE: Local interface in screener.ts
interface StockRecord { code: string; ... }
// AFTER: (removed, replaced with import)
import { type StockRecord } from "../schemas";

// BEFORE: Duplicate CacheStatistics in server.ts and stats.ts
interface CacheStatistics { marketData: { ... }; ... }
// AFTER:
import { type CacheStatistics } from "../schemas";
```

### 4.2 Automated Grep Patterns for Replacement

```bash
# Find all ConfigSchema imports from old path (11 files)
grep -rn 'from.*["'"'"'].*shared/schema["'"'"']' src/ --include="*.ts"

# Find all local interface declarations to remove
grep -rn '^interface \|^export interface ' src/ --include="*.ts" | grep -v schemas.ts

# Find duplicate CacheStatistics
grep -rn 'interface CacheStatistics' src/ --include="*.ts"

# Verify no remaining old imports after migration
grep -rn 'from.*shared/schema' src/ --include="*.ts"

# Verify no distributed schema files remain
grep -r 'from.*schemas/' src/ --include="*.ts" | grep -v 'src/schemas.ts'
```

### 4.3 Special Case: edinet.ts Exported Interfaces

`CompanyInfo`, `CompanyGovernance`, `FinancialData`, `CompanyDetail` are exported from `edinet.ts` but consumed via function return types (not direct type imports). The dashboard imports `getCompanyDetail`, `searchCompanies`, etc. — the types flow through function signatures.

**Migration approach**: After moving types to `src/schemas.ts`, update `edinet.ts` to import from `schemas.ts` and re-export functions only. The exported interfaces in `edinet.ts` can then be removed.

```typescript
// edinet.ts — AFTER migration
import { type CompanyInfo, type CompanyDetail, ... } from "../schemas";

// Function signatures remain unchanged — types are resolved via schemas.ts
export async function searchCompanies(query: string): Promise<CompanyInfo[]> { ... }
```

---

## 5. Risk & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Type inference breaks in downstream imports | Build failure | Medium | `bun x tsc --noEmit` after each phase |
| Zod schema doesn't match original interface exactly | Runtime validation crashes | Low | Convert interfaces 1:1, use `.passthrough()` where needed |
| `CacheStatistics` dedup causes missed fields | Dashboard/stats break | Low | Diff both definitions before merging |
| Circular dependency via new import path | Build failure | Very Low | `src/schemas.ts` has zero internal imports (leaf node) |
| `CompanyDetail extends CompanyInfo` pattern | Zod `.merge()` needed | Low | Use `CompanyInfoSchema.extend({...})` for composition |

### CDD Alignment

- All Zod `.parse()` calls crash on invalid data — no silent failures
- No `try-catch` around schema validation in business logic
- Stack traces from Zod validation errors are complete and actionable
- Infrastructure (Taskfile/Docker) handles retry if a process crashes due to bad data

---

## 6. Checklist for Task #13 (schema-migration-engineer)

### Pre-Migration

- [ ] Read and verify all 7 source files listed in Section 1
- [ ] Confirm `CacheStatistics` in server.ts and stats.ts are identical (or document diff)
- [ ] Confirm `CompanyDetail extends CompanyInfo` — use `z.intersection` or `.extend()` in Zod
- [ ] Verify `zod` is in `package.json` dependencies

### Phase 1: Create src/schemas.ts

- [ ] Create `src/schemas.ts` with all 13 schemas organized by domain
- [ ] Add backward-compat re-export in `src/shared/schema.ts`
- [ ] Run `bun x tsc --noEmit` — PASS

### Phase 2: Import Replacement

- [ ] Replace imports in 11 files that use `shared/schema`
- [ ] Remove local interfaces from `screener.ts` (3 interfaces)
- [ ] Remove local interfaces from `edinet.ts` (6 interfaces), update to import from schemas
- [ ] Remove local interface from `text.ts` (1 interface)
- [ ] Remove duplicate `CacheStatistics` from `server.ts` and `stats.ts`
- [ ] Remove local `Check` interface from `health_check.ts`
- [ ] Run `bun x tsc --noEmit` — PASS

### Phase 3: Cleanup & Verify

- [ ] Delete `src/shared/schema.ts`
- [ ] Run grep verification: `grep -r "from.*shared/schema" src/` returns 0
- [ ] Run grep verification: `grep -r "from.*schemas/" src/` returns 0
- [ ] Run `bun x tsc --noEmit` — PASS
- [ ] Smoke test: `bun run src/dashboard/server.ts` starts without error

### Rollback Plan

If any phase fails and cannot be resolved within 15 minutes:
1. `git checkout -- src/` to restore all source files
2. `src/schemas.ts` can be safely deleted (it's a new file)
3. No data or infrastructure changes — rollback is zero-risk
