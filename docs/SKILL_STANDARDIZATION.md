# Skill Standardization Migration Guide

Date: 2026-03-17

## What Changed

All 31 SKILL.md files in `.agent/skills/` were standardized to comply with the ECC SKILL.md template.

### Changes Applied

1. **Frontmatter**: Added `origin: local-git-analysis` field to all 31 skills
2. **Section Structure**: Mapped existing sections to ECC template's 4 required sections:
   - `Core Concepts` - key patterns, guidelines, do's and don'ts
   - `Code Examples` - practical implementation patterns
   - `Best Practices` - actionable guidelines
   - `When to Use` - specific scenarios and contexts

### Migration Strategy

Skills were grouped by their pre-existing structure pattern:

| Group | Pattern | Skills | Transformation |
|-------|---------|--------|---------------|
| A | Japanese (Expertise/Workflow/BP) | 10 skills | Section rename: Expertise -> Core Concepts, Workflow -> Code Examples |
| B | English (When to Use/Iron Rules/BP) | 7 skills | Section rename: Iron Rules -> Core Concepts, Usage Instructions -> Code Examples |
| C | Custom structure | 14 skills | Per-skill section mapping with targeted renames |

### Group A Skills (Japanese pattern)
alpha-mining, edinet, edinet-dataset-builder, fundamental-analysis, market-intelligence, polymarket, polymarket-alpha-miner, polymarket-data-validation, system-ops, trading-strategies

### Group B Skills (English pattern)
env-management, fail-fast-coding-rules, finmcp-analyst-workflows, fred-economic-data, qwen-local-inference, schema-management, where-to-save

### Group C Skills (Custom structure)
claude-expertise-bridge, frontend-design, harness-governance, harness-quality-pipeline, mixseek-backtest-engine, mixseek-competitive-framework, mixseek-data-pipeline, mixseek-ranking-scoring, powershell-bash-interop, qlib-investor-integration, typescript-agent-skills, vllm-io, vllm-qwen-agent-integration, web-ai-bridge

## Why

- Consistent structure enables agent trigger systems to reliably discover and invoke skills
- `origin` field supports provenance tracking for skill management via `agr`
- Standardized sections reduce cognitive load when authoring or reviewing skills
- Compliance with ECC template ensures interoperability across agent frameworks

## ECC SKILL.md Template Reference

```markdown
---
name: skill-name
description: Brief description with trigger phrases
origin: ECC  # or local-git-analysis
---

# Skill Title

Brief overview.

## Core Concepts
- Key patterns and guidelines

## Code Examples
(TypeScript + Python preferred)

## Best Practices
- Actionable guidelines

## When to Use
Specific scenarios and contexts.
```

## Validation

Run the validation command in `.agent/SKILLS_INVENTORY.md` to verify compliance.
