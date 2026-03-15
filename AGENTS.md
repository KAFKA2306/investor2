# Repository Guidelines (Slim Mode ✨)

## 📍 Key Locations

- **Logic**: `ts-agent/src/domain/` (Business rules)
- **I/O**: `ts-agent/src/io/` (API, File, DB)
- **ADRs**: `docs/adr/` (Architectural decisions)

## ⚙️ Core Operational Commands

- `task setup`: Install all dependencies
- `task check`: Reliability gate (lint + test + type check)
- `task run:newalphasearch`: Alpha discovery pipeline
- `task view`: Start API (:8787) and Dashboard (:5173)

## 🛡️ Governance (CRITICAL)

- **CDD (Crash-Driven Development)**: NO `try-catch`, NO defensive code. Let it crash, fix the root cause.
- **Deterministic Quality**: Biome (TS) and Ruff (Py). Automated via Hooks.
- **Schema-First**: Always use Zod (TS) or Pydantic (Py) at boundaries.
- **Minimal Changes**: Avoid over-engineering. Speed of iteration > Speculation.

## 🎯 Skill Management

- Sync via `agr sync`.
- Canonical source: `.agent/skills/`.
- Edit **only** in `.agent/skills/`.

---

*Refer to `CLAUDE.md` for specific agent instructions.*
