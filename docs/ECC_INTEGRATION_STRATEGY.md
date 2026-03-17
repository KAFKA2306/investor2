# ECC Integration Strategy for investor2

Date: 2026-03-17
Status: Draft

---

## 1. ECC Value Mapping

### 1.1 Agent Patterns (ECC 21 agents -> investor2)

ECC provides 21 specialized agents. Below maps the relevant ones to investor2's architecture.

| ECC Agent | Purpose | investor2 Equivalent | Action |
|-----------|---------|---------------------|--------|
| `planner` | Implementation planning | `newalphasearch` workflow | **SKIP** - workflow already covers this |
| `architect` | System design decisions | None (CLAUDE.md serves this role) | **SKIP** - CLAUDE.md + ADR sufficient |
| `tdd-guide` | Test-driven development | None | **ADOPT (Phase 2)** - useful for pipeline tests |
| `code-reviewer` | Code quality review | `harness-governance` skill | **MERGE** - extend existing skill |
| `security-reviewer` | Pre-commit security scan | `pre-tool-use.mjs` hook | **MERGE** - extend existing hook |
| `build-error-resolver` | Fix build errors | None | **ADOPT (Phase 3)** - Bun/TypeScript specific |
| `e2e-runner` | End-to-end testing | None | **DEFER** - not critical for quant pipeline |
| `refactor-cleaner` | Dead code cleanup | None | **ADOPT (Phase 2)** - useful for src/ cleanup |
| `doc-updater` | Documentation updates | None | **DEFER** - low priority |
| `observer` | Pattern learning | None | **EVALUATE (Phase 3)** - continuous-learning-v2 |

**Verdict**: 3 agents worth adopting, 2 worth merging into existing tools. Remaining 16 are either redundant with existing investor2 patterns or irrelevant to the quant domain.

### 1.2 Skill Categories (ECC 102 skills -> investor2 31 skills)

| ECC Skill Category | Count | investor2 Coverage | Gap |
|-------------------|-------|-------------------|-----|
| Coding standards | ~15 | `fail-fast-coding-rules`, `harness-governance` | **Covered** (CDD is stricter) |
| Testing patterns | ~12 | None | **Gap** - Phase 2 candidate |
| Language-specific (TS/JS) | ~20 | `typescript-agent-skills` | **Partially covered** |
| Security | ~8 | `pre-tool-use.mjs` | **Partially covered** |
| Git/workflow | ~10 | `git.md` workflow | **Covered** |
| Documentation | ~8 | None | **Low priority** |
| Token optimization | ~5 | None | **Gap** - Phase 1 candidate |
| Continuous learning | ~6 | None | **Gap** - Phase 3 candidate |
| Domain-specific | ~18 | 20+ domain skills (alpha, polymarket, edinet) | **investor2 is stronger here** |

**Verdict**: investor2 already exceeds ECC in domain skills. Key gaps are: token optimization, testing patterns, and continuous learning.

### 1.3 Hooks & Rules (ECC 8 hooks + 34 rules -> investor2)

| ECC Hook | Purpose | investor2 Status | Action |
|----------|---------|------------------|--------|
| `PreToolUse: Bash` | Auto-tmux dev servers | Not needed | **SKIP** |
| `PreToolUse: Edit\|Write` | Suggest compaction | None | **ADOPT (Phase 1)** - token savings |
| `PostToolUse: Edit` | Auto-format after edits | None | **ADOPT (Phase 1)** - run Biome |
| `PostToolUse: Edit` | TypeScript check after edits | None | **ADOPT (Phase 1)** - run tsc |
| `SessionStart` | Load previous context | None | **ADOPT (Phase 2)** - session persistence |
| `Stop` | Persist session state | None | **ADOPT (Phase 2)** - session persistence |

| ECC Rule Category | investor2 Status | Conflict? |
|-------------------|------------------|-----------|
| Security rules | Partially via CDD | No conflict |
| Coding style rules | Biome + CDD | **Minor conflict** (see Section 2) |
| Testing requirements | None | No conflict |
| Error handling rules | CDD overrides | **Major conflict** (see Section 2) |

---

## 2. Conflict Analysis

### 2.1 CDD vs ECC Error Handling - RECONCILIATION REQUIRED

**The core tension**: ECC assumes standard defensive programming (try-catch, error boundaries, graceful degradation). investor2 enforces CDD (Crash-Driven Development) which **prohibits** all of these.

| Aspect | ECC Pattern | CDD Rule | Resolution |
|--------|------------|----------|------------|
| try-catch | Encouraged in agents | **Prohibited** in business logic | **CDD wins** - CDD is non-negotiable per CLAUDE.md |
| Error boundaries | React error boundaries | Not applicable (no React) | N/A |
| Graceful degradation | Return defaults on failure | **Prohibited** - crash instead | **CDD wins** |
| Retry logic | In-code retries | Infrastructure-only (Taskfile/Docker) | **CDD wins** |
| Null checks | Defensive null handling | Let it crash | **CDD wins** |

**Reconciliation strategy**: Import ECC patterns **only** for infrastructure-layer code (`src/io/`, `src/db/`, hooks). Business logic (`src/agents_*`, `src/domain_*`, `src/pipeline_*`) remains strict CDD. This aligns with CDD Rule 3 (Separation of Concerns).

### 2.2 CLAUDE.md Rules vs ECC Patterns

| investor2 Rule | ECC Pattern | Conflict? | Resolution |
|---------------|-------------|-----------|------------|
| Unified schemas (`src/schemas.ts`) | No equivalent | No | Keep investor2 rule |
| PathRegistry for all paths | No equivalent | No | Keep investor2 rule |
| `snake_case.ts` file naming | ECC uses `kebab-case` | **Minor** | Keep investor2 convention |
| Biome (not ESLint/Prettier) | ESLint/Prettier assumed | **Minor** | Keep Biome, adapt hooks |
| `agr` for skill management | Manual skill files | **Minor** | Keep agr, adopt ECC templates |
| No `src/agents/` directory | `agents/` directory standard | **Minor** | Keep flat `agents_*.ts` pattern |

### 2.3 Token Optimization Integration

ECC defaults to Sonnet + Haiku subagents with `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50`. investor2 currently has no token optimization strategy.

**Recommendation**: Adopt ECC's token settings as-is. No conflict with CDD.

```json
{
  "env": {
    "CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "50"
  }
}
```

---

## 3. Implementation Roadmap

### Phase 1: Low-Risk (1-2 days)

Zero code changes. Configuration and documentation only.

| Item | What | Where | Effort |
|------|------|-------|--------|
| Token optimization | Add autocompact setting | `.claude/settings.json` | 10 min |
| Post-edit auto-format hook | Run `biome check --fix` after Edit | `.agent/hooks/` or settings.json hooks | 30 min |
| Post-edit type-check hook | Run `bun tsc --noEmit` after `.ts` edits | `.agent/hooks/` or settings.json hooks | 30 min |
| ADR: ECC adoption decision | Document why/what we adopt | `docs/adr/` | 30 min |
| Command-Skill map | Document investor2's command->skill mapping | `docs/COMMAND-SKILL-MAP.md` | 1 hr |

### Phase 2: Medium-Risk (3-5 days)

Skill standardization and new capabilities.

| Item | What | Where | Effort |
|------|------|-------|--------|
| SKILL.md template standardization | Adopt ECC frontmatter format (name, description, tools, model) for all 31 skills | `.agent/skills/*/SKILL.md` | 2 hrs |
| Session persistence hooks | `SessionStart` + `Stop` hooks for context carryover | `.agent/hooks/` | 1 day |
| Testing skill | Adapt ECC `tdd-guide` for Bun test runner | `.agent/skills/tdd-guide/` | 1 day |
| Refactor-cleaner skill | Adapt ECC pattern for dead code detection in `src/` | `.agent/skills/refactor-cleaner/` | 0.5 day |
| Merge code-reviewer into harness-governance | Extend existing governance skill with ECC review checklist | `.agent/skills/harness-governance/` | 0.5 day |

### Phase 3: High-Risk (1-2 weeks)

Agent pattern integration and learning systems. Requires careful testing.

| Item | What | Where | Effort |
|------|------|-------|--------|
| Orchestrate command | Multi-agent workflow chaining (planner->reviewer->security) | `.agent/workflows/orchestrate.md` | 2 days |
| continuous-learning-v2 | Instinct system for pattern learning across sessions | `.agent/skills/continuous-learning-v2/` | 3 days |
| Build-error-resolver agent | Auto-fix Bun/TypeScript build errors | `.agent/skills/build-error-resolver/` | 1 day |
| Agent model routing | Route complex tasks to Opus, simple to Haiku | settings.json + skill frontmatter | 1 day |

---

## 4. Quick Decision Table

### MUST-HAVE vs NICE-TO-HAVE

| Pattern | Priority | Phase | Rationale |
|---------|----------|-------|-----------|
| Post-edit auto-format (Biome) | **MUST** | 1 | Prevents formatting drift, zero risk |
| Post-edit type-check | **MUST** | 1 | Catches type errors immediately |
| Token optimization settings | **MUST** | 1 | Free token savings, no downside |
| SKILL.md frontmatter standardization | **MUST** | 2 | Required for agent trigger system (CLAUDE.md states "non-negotiable") |
| Session persistence | **SHOULD** | 2 | Reduces context loss between sessions |
| Testing skill (tdd-guide) | **SHOULD** | 2 | Pipeline reliability improvement |
| Refactor-cleaner | **NICE** | 2 | Useful but not blocking |
| Orchestrate workflow | **NICE** | 3 | Only needed for multi-step features |
| Continuous learning | **NICE** | 3 | Long-term value, high implementation cost |
| Build-error-resolver | **NICE** | 3 | Convenience, not critical |

### Dependencies

```
Phase 1 (no dependencies)
  |
  v
Phase 2 (depends on Phase 1 hooks infrastructure)
  |
  v
Phase 3 (depends on Phase 2 skill standardization)
```

### Decision Matrix

| Option | Scope | Risk | Token Cost | Recommendation |
|--------|-------|------|------------|----------------|
| **A: Minimal** | Phase 1 only | Near-zero | Saves tokens | Good for immediate gains |
| **B: Recommended** | Phase 1 + Phase 2 | Low-Medium | Neutral | Best ROI, covers key gaps |
| **C: Full Adoption** | All phases | Medium-High | Higher (more hooks) | Only if Phase 2 proves valuable |

**Recommended path**: Start with Option A immediately, evaluate after 1 week, proceed to B if no regressions.

---

## Appendix: ECC Patterns Explicitly Rejected

| Pattern | Reason |
|---------|--------|
| ESLint/Prettier hooks | investor2 uses Biome exclusively |
| React error boundaries | No React in codebase |
| `agents/` directory structure | Conflicts with flat `agents_*.ts` convention |
| In-code retry logic | Violates CDD Rule 3 |
| Defensive error handling rules | Violates CDD Rule 1 |
| Language-specific rules (Go, Rust, Swift, Python) | investor2 is TypeScript-first |
| MCP server configs | investor2 manages MCP separately |
