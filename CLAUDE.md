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

**src/ (code — ACCEPT DISTRIBUTION, NO NEW AGENT DIR):**
```
src/
├── commands/       # Taskfile-driven CLI scripts (data sync, stats)
├── dashboard/      # Frontend & UI
├── features/       # Feature implementations (enrichment, calculations)
├── io/             # Data input/output (APIs, files, DB, gateways)
├── utils/          # Generic utilities & helpers
├── shared/         # Shared code, constants, helpers
├── preprocess/     # Data preprocessing pipelines
├── context/        # Context/memory management
├── schemas.ts      # Unified Zod schemas (MANDATORY: single file)
└── index.ts        # Entry point
```

**KEY PRINCIPLE**:
- ✅ **Accept current distribution** — src/agents/ NOT created; agent implementations stay distributed (agents_*.ts)
- ✅ **src/commands/** — REQUIRED for Taskfile task implementations
- ⚠️ **File prefixes** — Minimize but accept where established (e.g., `agents_polymarket_orchestrator.ts`)

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

## 🎯 Skill & Agent Management (CRITICAL)

### Skill Management
- **Canonical source**: `.agent/skills/<name>/SKILL.md` (managed by `agr`)
- `.claude/skills/` is a **symlink** to `.agent/skills/` — physically the same directory
- **Edit only** `.agent/skills/` — `.claude/skills/` reflects changes instantly
- Each SKILL.md requires YAML frontmatter: `name` + English `description` with trigger phrases
- **All 40 skills** must have frontmatter (non-negotiable for agent trigger system)

### Agent Management
- ✅ **Only in `.agent/`** — skills, workflows, hooks (agr-managed)
- ❌ **NOT in src/** — no TypeScript or Python agent implementations
- ❌ **NOT in separate agent files** — use skills + workflows for orchestration
- Agent orchestration via: `.agent/workflows/newalphasearch.md`, `.agent/skills/claude-expertise-bridge/SKILL.md`

### Critical SKILLs

| SKILL | Purpose |
|-------|---------|
| `schema-management` | Enforce unified schema architecture in `src/schemas.ts` |
| `fail-fast-coding-rules` | Enforce CDD patterns (no try-catch, let errors cascade) |
| `where-to-save` | Enforce PathRegistry for all file operations |
| `harness-governance` | Enforce repository hygiene and ADR enforcement |
| `claude-expertise-bridge` | Meta-skill for agent orchestration & decision logic |

---

## 🚨 Guardrail Registry (Failure Prevention)

**Purpose**: Record all detected failure patterns so AI never repeats the same bug twice.

**Implementation**:
- When a failure occurs, document it in a **Guardrail note** (inline in CLAUDE.md under this section, or as an ADR in `docs/adr/`)
- **Example pattern to record**:
  ```
  GUARD-001: Alpha formula without normalization
  → Failure: Formula lacks Rank() or CS_ZScore() normalization
  → Fix: Always append Rank() before final return
  → Enforced by: alpha-mining SKILL, Phase 1 validation
  ```

---

## 📊 Experiment Tracking (EXP / child-exp)

**2-Level Experiment Hierarchy**:
- **EXP** (Major Cycle): Large changes (prompt redesign, new SKILL, workflow overhaul, domain pivot).
  - Use: `task run:newalphasearch --exp "EXP-YYYYMMDD-NNN: [Title]"`
  - Log to: `EXP_SUMMARY.md` (Experiment Index section).

- **child-exp** (Micro-Iteration): Small tweaks within an EXP (threshold ±5%, single operator swap, prompt rewording).
  - Use: `task run:newalphasearch --child-exp "EXP-child-YYYYMMDD-NNN: [Change]"`
  - Log to: Parent EXP section (collapse child exps to keep index readable).

**Metrics to Track**:
1. Sharpe Ratio (baseline: ≥1.5)
2. Information Coefficient (baseline: ≥0.04)
3. Max Drawdown (absolute ceiling: ≤0.10)
4. Candidate Generation Rate (unique formulas per cycle)
5. GO/HOLD/PIVOT distribution

**Decision Logic**:
- ✅ **GO**: All thresholds passed → Deploy immediately.
- 🔀 **HOLD**: 1-2 metrics marginal → child-exp refinement.
- 🔄 **PIVOT**: 2+ critical failures → Ralph Loop domain switch.

---

## 📖 ECC Integration (Phase 1)

ECC (Extended Claude Code) patterns adopted under strict CDD compliance. ECC applies to **infrastructure layers only** (`src/io/`, hooks, `.agent/`). Business logic remains strict CDD.

**Key documents**:
- `docs/ECC_REFERENCE.md` — Pattern definitions (Tool Use Loop, Verification Loop, etc.)
- `docs/SKILL_DEVELOPMENT_GUIDE.md` — Skill template, checklist, lifecycle
- `docs/AGENT_PATTERNS.md` — Agent-specific pattern mappings
- `docs/ECC_INTEGRATION_STRATEGY.md` — Full strategy with conflict analysis

**ADRs**:
- `docs/adr/004-ecc-integration.md` — ECC adoption decision (Option B: Phase 1 + Phase 2)
- `docs/adr/003-agent-pattern-integration.md` — Agent pattern integration decision

**Token optimization** (active):
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50`
- Default model: Sonnet (routine), Opus (architectural)
- Thinking token limit: 8000 max

---
*For task-specific commands and setup, see [OPERATIONS.md](file:///home/kafka/finance/investor/docs/OPERATIONS.md).*
