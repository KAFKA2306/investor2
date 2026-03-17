# Skill Development Guide

How to create, test, and maintain skills for the investor project.

---

## SKILL.md Template

Every skill lives in `.agent/skills/<name>/SKILL.md` with this structure:

```markdown
---
name: skill-name
description: >
  English description with trigger phrases. Example: "Use this skill when
  reviewing alpha formulas for DSL correctness and normalization compliance."
---

# Skill Name

## Purpose
One sentence explaining what the skill does and when it activates.

## Trigger Conditions
- Specific phrases or contexts that should activate this skill
- Example: "review alpha", "check DSL", "validate formula"

## Instructions
Step-by-step instructions the agent follows when this skill is active.

1. First action
2. Second action
3. Verification step

## Constraints
- What the skill must NOT do
- CDD compliance requirements
- Scope boundaries

## References
- Related files, docs, or other skills
```

---

## Frontmatter Requirements

Every SKILL.md MUST have YAML frontmatter with these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Kebab-case skill identifier matching directory name |
| `description` | Yes | English description with trigger phrases for the agent trigger system |

The `description` field is critical -- the agent trigger system matches user intent against these descriptions. Include specific phrases users would say to invoke the skill.

---

## Checklist for New Skills

Before declaring a skill complete:

- [ ] SKILL.md exists at `.agent/skills/<name>/SKILL.md`
- [ ] YAML frontmatter has `name` and `description` fields
- [ ] Description includes trigger phrases in English
- [ ] Skill name matches directory name (kebab-case)
- [ ] Instructions are specific and actionable (not vague guidance)
- [ ] CDD constraints documented (no try-catch in generated code)
- [ ] Tested: trigger phrases activate the skill correctly
- [ ] Registered in `agr.toml` via `agr add`

---

## When to Create a Skill vs Command vs Agent

| Mechanism | Use When | Location |
|-----------|----------|----------|
| **Skill** | AI agent needs domain-specific instructions for a recurring task | `.agent/skills/<name>/SKILL.md` |
| **Command** | Human or Taskfile needs to run a script | `src/commands/` + `Taskfile.yml` |
| **Workflow** | Multi-step orchestration across skills/agents | `.agent/workflows/<name>.md` |

Do NOT create a skill for one-off tasks. Skills are for patterns that recur across sessions.

---

## Existing Skills (31 total)

Organized by domain:

**Alpha Discovery**: `alpha-mining`, `harness-quality-pipeline`
**Data**: `edinet`, `edinet-dataset-builder`, `fred-economic-data`, `mixseek-data-pipeline`
**Polymarket**: `polymarket`, `polymarket-alpha-miner`, `polymarket-data-validation`
**Governance**: `harness-governance`, `fail-fast-coding-rules`, `env-management`
**Analysis**: `fundamental-analysis`, `market-intelligence`, `finmcp-analyst-workflows`
**Infrastructure**: `claude-expertise-bridge`, `frontend-design`
**Mixseek**: `mixseek-backtest-engine`, `mixseek-competitive-framework`, `mixseek-ranking-scoring`

For the full list: `ls .agent/skills/`

---

## Skill Lifecycle

1. **Create**: Write SKILL.md following the template above
2. **Register**: `agr add` to track in `agr.toml`
3. **Test**: Verify trigger phrases work in a Claude Code session
4. **Iterate**: Update instructions based on execution feedback
5. **Deprecate**: Remove from `.agent/skills/` and `agr.toml` when no longer needed

---

## ECC Skill Patterns (Phase 2)

Skills planned for adoption from ECC:

| Skill | Purpose | Phase |
|-------|---------|-------|
| `tdd-guide` | Test-driven development instructions for Bun test runner | Phase 2 |
| `refactor-cleaner` | Dead code detection and cleanup in `src/` | Phase 2 |
| `build-error-resolver` | Auto-fix Bun/TypeScript build errors | Phase 3 |

These will follow the same template and checklist above.
