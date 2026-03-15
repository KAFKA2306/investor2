---
name: schema-management
description: >
  MANDATORY TRIGGER: Invoke BEFORE adding, modifying, or creating any Zod schema,
  type definition, or validation logic. If the request involves data validation
  schemas, model definitions, API contracts, or request/response types, this skill
  must be used to enforce the unified schema architecture.
---

# Unified Schema Management

All data validation, type definitions, and model contracts are consolidated in a single source of truth.

## 🚀 When to Use

- Adding new Zod schemas (API payloads, domain models, validation rules)
- Creating TypeScript type definitions or interfaces that need validation
- Defining request/response contracts for APIs or inter-agent communication
- Implementing validation logic or schema inference
- Reviewing code that instantiates schemas from other modules

## 📍 Single Source of Truth

**Location**: `src/schemas.ts`

All schemas, type definitions, enums, interfaces, validation functions, and constants must be centralized here.

### Rule 1: NO DISTRIBUTED SCHEMA FILES

❌ **FORBIDDEN**:
```
src/schemas/user_schema.ts
src/models/payment_schema.ts
src/api/contract_schemas.ts
src/domain/financial_schemas.ts
```

✅ **CORRECT**:
```
src/schemas.ts (single file with all schemas)
```

### Rule 2: ORGANIZATION WITHIN SINGLE FILE

Within `src/schemas.ts`, group logically related schemas:

```typescript
// Allocation & Investment (related schemas grouped)
export const InvestmentIdeaSchema = z.object({ ... });
export const AllocationRequestSchema = z.object({ ... });
export const AllocationResultSchema = z.object({ ... });

// Polymarket Trading (separate logical group)
export const MarketSchema = z.object({ ... });
export const SignalSchema = z.object({ ... });

// Event System (another logical group)
export const EventTypeSchema = z.enum([...]);
export const BaseEventSchema = z.object({ ... });
```

### Rule 3: CONSISTENT NAMING

All schema identifiers follow the pattern: `<EntityName>Schema` (not `<EntityName>Validation` or `<EntityName>Type`).

```typescript
✅ export const UserSchema = z.object({ ... });
❌ export const UserValidation = z.object({ ... });
❌ export const User = z.object({ ... });

✅ export type User = z.infer<typeof UserSchema>;
❌ export interface User { ... }  // (unless it has no validation)
```

### Rule 4: TYPE INFERENCE FROM SCHEMA

Always use `z.infer<typeof Schema>` for types. Never duplicate definitions.

```typescript
export const PaymentSchema = z.object({
  amount: z.number().positive(),
  currency: z.string(),
});

✅ export type Payment = z.infer<typeof PaymentSchema>;
❌ export interface Payment { amount: number; currency: string; }
```

### Rule 5: VALIDATION FUNCTIONS

Validation functions (like `validateQlibFormula`) belong in `src/schemas.ts` with their supporting constants.

```typescript
export const QLIB_ALLOWED_COLUMNS = new Set([...]);
export function validateQlibFormula(formula: string): { ... }
```

### Rule 6: ENUMS & CONSTANTS

All enums, record types, and constants related to schemas must coexist in `src/schemas.ts`.

```typescript
export enum AlphaStatus { ACTIVE, INACTIVE, DECAYED }
export const EdinetDocumentTypeLabel: Record<...> = { ... };
```

## 📋 Import Pattern

From anywhere in the codebase:

```typescript
import {
  InvestmentIdeaSchema,
  type InvestmentIdea,
  AllocationResultSchema,
  AlphaStatus,
  validateQlibFormula,
} from "../schemas.ts";
```

**NOT**:
```typescript
❌ import { InvestmentIdeaSchema } from "../schemas/allocation_schema.ts";
❌ import { AlphaStatus } from "../domain/enums.ts";
```

## 🛡️ Enforcement

### Pre-commit Check
```bash
grep -r "from.*schemas/" src --include="*.ts" | grep -v "src/schemas.ts"
# Should return 0 results
```

### Architecture Rule
If any TypeScript file imports from a path matching `src/schemas/.*\.ts` (except `src/schemas.ts`), the import is a violation.

## ✅ Best Practices

1. **Keep Related Schemas Together**: Group by domain/feature, not by type
2. **Document with Zod Descriptions**: Use `.describe()` for clarity
3. **Export All Types**: Every schema must have its inferred type exported
4. **Validate at Boundaries**: Use schemas only at I/O boundaries; domain logic receives already-validated types
5. **No Circular Imports**: If schemas reference each other, they must be in the same file

## 🚫 Violations & Consequences

| Violation | Consequence |
|-----------|------------|
| Create new schema file in `src/schemas/` | Import path breaks; code fails at runtime |
| Duplicate schema definition in multiple files | Type divergence; validation inconsistency |
| Use `interface` instead of `z.infer<typeof>` | Loss of validation; type safety gaps |
| Import schema from wrong path | Module resolution error; CI/CD failure |

---

**Reference**: `CLAUDE.md` project structure section defines consolidated schema architecture.
