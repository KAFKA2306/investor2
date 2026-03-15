# CLAUDE.md (Slim Mode 🥗)

Project guidance for Claude Code. Operational details are in [OPERATIONS.md](file:///home/kafka/finance/investor/docs/OPERATIONS.md).

## 🏛️ Architecture SSOT

Refer to `docs/diagrams/` for precedence.
This is a multi-agent quant system: `src/system/pipeline_orchestrator.ts` is the entry point.

| Role | Responsibility |
|---|---|
| Orchestrator | Full pipeline control |
| Elder | Unified memory/persistence |
| Data | PIT-clean data delivery |
| Quant | Factor mining & backtest |

## 📍 Data Path Rules (CRITICAL)

**Unified Source of Truth**: `/mnt/d/investor_all_cached_data/`
**Rule**: NEVER hardcode filesystem paths. Use `PathRegistry` from `src/system/path_registry.ts`.
See `DATA_STRUCTURE.md` for the unified architecture mappings.

## 🛠️ Coding Conventions

- **Formatter/Linter**: Biome (`config/biome.json`)
- **Naming**: `snake_case.ts` (files), `PascalCase` (classes), `camelCase` (vars).
- **Agents**: Extend `BaseAgent` and implement `run()`.
- **Validation**: Use Zod schemas in unified `src/schemas.ts` only. See **Unified Schemas** section below.
- **CDD (Crash-Driven Development)**:
    - **No `try-catch`**: prohibited in business logic; let errors cascade.
    - **No Defensive Returns**: never return `null`/`false` to hide failures.
    - **Infrastructure Resilience**: retries/timeouts belong in `Makefile`/Docker/K8s only.
    - **Stack Traces**: treat as the inviolable ground truth; never suppress.
- **Commits**: Follow Conventional Commits (`feat:`, `fix:`, etc.).

## 📂 Project Structure (Optimized)

**Root level (4 files only — tool standard positions):**
- `Taskfile.yml` — task execution entry point
- `package.json` — npm/bun manifest
- `pyproject.toml` — Python/uv manifest
- `tsconfig.json` — TypeScript config

**config/ (consolidated settings):**
- `default.yaml` — master config (paths, risk, polymarket, quant, alpha, models, constants unified)
- `biome.json` — formatter/linter config (JSON only; YAML not supported)

**.agent/ (agent resources):**
- `agr.toml` — Agent Resource manifest

**Rule**: Do NOT add files to root. New configs go to `config/`. Biome config must stay JSON (not YAML).

## 📦 Unified Schemas (MANDATORY)

**Single Source of Truth**: `src/schemas.ts`

All Zod schemas, type definitions, enums, constants, and validation functions must be consolidated in this single file. No distributed schema files.

### Rule 1: ALL schemas live in `src/schemas.ts`

❌ **FORBIDDEN**:
```
src/schemas/user_schema.ts
src/models/payment_schema.ts
src/domain/financial_schemas.ts
```

✅ **CORRECT**:
```
src/schemas.ts (single file with all schemas, organized by domain)
```

### Rule 2: Consistent Pattern

Each schema follows:
```typescript
export const EntitySchema = z.object({ ... });
export type Entity = z.infer<typeof EntitySchema>;
```

- Schema identifier: `<EntityName>Schema` (not `<EntityName>Validation`)
- Types use `z.infer<typeof>` (never duplicate interface definitions)

### Rule 3: Logical Grouping

Within `src/schemas.ts`, organize by domain:
```typescript
// Allocation & Investment
export const InvestmentIdeaSchema = z.object({ ... });
export const AllocationRequestSchema = z.object({ ... });

// Polymarket Trading
export const MarketSchema = z.object({ ... });
export const SignalSchema = z.object({ ... });

// Event System
export const EventTypeSchema = z.enum([...]);
export const BaseEventSchema = z.object({ ... });
```

### Rule 4: Import Pattern

From anywhere:
```typescript
import {
  InvestmentIdeaSchema,
  type InvestmentIdea,
  AlphaStatus,
  validateQlibFormula,
} from "../schemas.ts";
```

NOT from `src/schemas/*`

### Rule 5: Enforcement

Use the `schema-management` SKILL to enforce this rule during code review.
Pre-commit: `grep -r "from.*schemas/" src --include="*.ts" | grep -v "src/schemas.ts"` should return 0 results.

## 🎯 Skill Management (CRITICAL)

- **Canonical source**: `.agent/skills/<name>/SKILL.md` (managed by `agr`)
- `.claude/skills/` is a **symlink** to `.agent/skills/` — physically the same directory
- **Edit only** `.agent/skills/` — `.claude/skills/` reflects changes instantly
- Each SKILL.md requires YAML frontmatter: `name` + English `description` with trigger phrases
- **TypeScript runtime skills** (different from above): `ts-agent/src/skills/` — see `typescript-agent-skills` SKILL.md

### Critical SKILLs

| SKILL | Purpose |
|-------|---------|
| `schema-management` | Enforce unified schema architecture in `src/schemas.ts` |
| `fail-fast-coding-rules` | Enforce CDD patterns (no try-catch, let errors cascade) |
| `where-to-save` | Enforce PathRegistry for all file operations |
| `harness-governance` | Enforce repository hygiene and ADR enforcement |

---
*For task-specific commands and setup, see [OPERATIONS.md](file:///home/kafka/finance/investor/docs/OPERATIONS.md).*
