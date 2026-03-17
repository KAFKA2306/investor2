# ADR-004: ECC Integration Strategy

## Status

Accepted

## Date

2026-03-17

## Context

The investor project uses Crash-Driven Development (CDD) as its core development philosophy. ECC (Extended Claude Code) provides 21 agents, 102 skills, 8 hooks, and 34 rules for Claude Code agent workflows. These two systems have a fundamental tension: ECC assumes defensive programming while CDD prohibits it.

The project needs to adopt valuable ECC patterns (token optimization, post-edit hooks, session persistence, skill standardization) without compromising CDD constraints (no try-catch in business logic, crash on failure, infrastructure-only resilience).

## Decision

### Option B selected: Phase 1 + Phase 2 adoption

1. **CDD is non-negotiable**. All ECC patterns that conflict with CDD error handling are rejected or adapted.

2. **ECC applies to infrastructure layers only** (`src/io/`, hooks, configuration, `.agent/`). Business logic (`src/domain/`, agents) remains strict CDD.

3. **Phase 1 (immediate, 1-2 days)**:
   - Token optimization: `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=50`, Sonnet default, 8000 thinking token limit
   - Post-edit hooks: Biome auto-format, TypeScript type-check after `.ts` edits
   - CLAUDE.md restructured with 5 new ECC-aligned sections
   - Documentation: `docs/ECC_REFERENCE.md`, `docs/SKILL_DEVELOPMENT_GUIDE.md`

4. **Phase 2 (3-5 days)**:
   - SKILL.md frontmatter standardization across all 31 skills
   - Session persistence hooks (SessionStart + Stop)
   - `tdd-guide` skill adoption for Bun test runner
   - `harness-governance` skill extension with ECC review checklist

5. **Phase 3 (deferred, 1-2 weeks)**:
   - Continuous Learning v2 instinct system
   - Build-error-resolver agent
   - Agent model routing (Opus for complex, Haiku for simple)

### Explicitly rejected ECC patterns

| Pattern | Reason |
|---------|--------|
| In-code retry logic | Violates CDD Rule 3 (separation of concerns) |
| Defensive error handling | Violates CDD Rule 1 (exception handling) |
| ESLint/Prettier | investor2 uses Biome |
| `agents/` directory structure | Conflicts with flat `agents_*.ts` convention |
| React error boundaries | No React in codebase |
| Language-specific rules (Go, Rust, Swift) | investor2 is TypeScript-first |

## Consequences

- Token costs decrease via autocompact and model routing without code changes.
- Post-edit hooks catch formatting and type errors immediately, reducing review cycles.
- Skill standardization enables reliable agent trigger matching across all 31 skills.
- CDD remains the authority for all error handling decisions.
- Phase 2 and Phase 3 depend on Phase 1 infrastructure; no phase can be skipped.
- Full strategy details: `docs/ECC_INTEGRATION_STRATEGY.md`.
- Pattern reference: `docs/ECC_REFERENCE.md`.
