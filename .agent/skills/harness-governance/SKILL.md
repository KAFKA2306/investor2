---
name: harness-governance
description: MANDATORY TRIGGER: Invoke for any task involving repository hygiene, documentation rot, ADR enforcement, or linter-driven self-healing. If the request mentions lint errors, outdated READMEs, structural debt, or "rot", this skill must be used to enforce Harness Engineering standards.
origin: local-git-analysis
---

# Harness Governance Skill

This skill enforces the **Harness Engineering** best practices via external executable tools. Do not memorize rules; execute the harness.

## When to Use
Use when working with harness governance related tasks.

## Core Concepts

When triggered, you MUST immediately rely on the following external sources of truth:

1. **Repository Rules & Structure**: Refer to `AGENTS.md` and `CLAUDE.md`. They contain the complete, up-to-date governance rules (Crash-Driven Development, deterministic quality, etc.).
2. **Code Quality & Linting**: Use `harness-quality-pipeline` skill to install and run hooks. Biome config (`config/biome.json`) defines all lint/format rules.
3. **Garbage Collection**: If rotting files or dead code are suspected, investigate manually. Remove only after verifying they are truly unused.
4. **Architecture Decisions**: Review `docs/adr/`. Any architectural change MUST be recorded there.

## Code Examples
See detailed sections for implementation patterns and examples.

## Best Practices

**DO NOT** maintain checklists or procedural instructions within this `SKILL.md` file. Treat this file ONLY as a directory of pointers to executable scripts and canonical markdown files to prevent context bloat and synchronization debt.
