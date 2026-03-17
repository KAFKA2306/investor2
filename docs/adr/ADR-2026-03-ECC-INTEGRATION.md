# ADR-2026-03: ECC Integration Strategy

## Status: ACCEPTED (Phase 1 complete)

## Date: 2026-03-17

## Context

- investor2 has a strong CDD (Crash-Driven Development) foundation: no try-catch, error cascade, stack traces as ground truth
- ECC (Everything Claude Code) provides 102+ skills, 21+ agents, and proven automation patterns
- Token cost is critical for continuous alpha discovery loops (run:newalphasearch)
- Global `~/.claude/settings.json` already implements PostToolUse hooks for auto-formatting (biome, ruff, gofumpt)

## Decision

Adopt ECC patterns **selectively** via a two-phase approach:

### Phase 1: Token Optimization + Hooks (1-2 days)
- Token optimization config at `~/.claude/global-patterns/token-optimization-config.yaml`
- Project hook architecture documented at `config/hooks.json`
- Runtime hooks remain in `~/.claude/settings.json` (PostToolUse for auto-format/lint)
- This ADR created to record the decision

### Phase 2: SKILL.md Standardization + Continuous Learning (3-5 days)
- Standardize all 40 SKILL.md files with YAML frontmatter
- Integrate ECC continuous-learning patterns
- Add session persistence hooks

## Constraints

- **CDD is non-negotiable**: No try-catch in business logic, no defensive returns
- **Infrastructure-only resilience**: Retry/timeout logic stays in Taskfile/Docker/K8s
- **Unified schemas**: All Zod schemas in `src/schemas.ts` only
- **PathRegistry**: No hardcoded filesystem paths

## Consequences

- Token costs reduced through model routing and compaction triggers
- Post-edit quality maintained via existing global hooks
- ECC patterns adapted to respect CDD boundaries
- All hook commands reference existing Taskfile tasks (format, lint, typecheck, check)

## Rationale

Option B (Phase 1 + Phase 2) provides highest ROI without breaking existing architecture.
ECC's full pattern library is too broad for direct adoption; selective integration preserves
CDD guarantees while gaining token optimization and automation benefits.
