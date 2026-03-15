---
name: harness-governance
description: MANDATORY TRIGGER: Invoke for any task involving repository hygiene, documentation rot, ADR enforcement, or linter-driven self-healing. If the request mentions lint errors, outdated READMEs, structural debt, or "rot", this skill must be used to enforce Harness Engineering standards.
---

# Harness Governance Skill

This skill enforces the **Harness Engineering** best practices via external executable tools. Do not memorize rules; execute the harness.

## 🚨 MANDATORY PROTOCOL

When triggered, you MUST immediately rely on the following external sources of truth:

1. **Repository Rules & Structure**: Execute `view_file` on `AGENTS.md`. It contains the complete, up-to-date governance rules (Crash-Driven Development, deterministic quality, etc.).
2. **Hygiene & Linting**: Execute `run_command` with `bash scripts/self_healing_lint.sh`. Follow the instructions provided in its output EXACTLY.
3. **Garbage Collection**: If rotting files or dead code are suspected, execute `run_command` with `task maintenance:gc`.
4. **Architecture Decisions**: Execute `list_dir` on `docs/adr/`. Any architectural change MUST be recorded here.

## ⚠️ CRITICAL INSTRUCTION

**DO NOT** maintain checklists or procedural instructions within this `SKILL.md` file. Treat this file ONLY as a directory of pointers to executable scripts and canonical markdown files to prevent context bloat and synchronization debt.
