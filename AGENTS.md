# Repository Guidelines (Slim Mode)

## 📍 Key Locations

- **Logic**: `ts-agent/src/domain/` (Business rules)
- **I/O**: `ts-agent/src/io/` (API, File, DB)
- **ADRs**: `docs/adr/` (Architectural decisions)

## ⚙️ Core Operational Commands

- `task setup`: Install all dependencies
- `task check`: Reliability gate (lint + test + type check + external snapshot audit)
- `task run:newalphasearch`: Alpha discovery pipeline
- `task view`: Start API (:8787) and Dashboard (:5173)

## 🛡️ Governance (CRITICAL)

- **CDD (Crash-Driven Development)**: NO `try-catch`, NO defensive code. Let it crash, fix the root cause.
- **Deterministic Quality**: Biome (TS) and Ruff (Py). Automated via Hooks.
- **Schema-First**: Always use Zod (TS) or Pydantic (Py) at boundaries.
- **Minimal Changes**: Avoid over-engineering. Speed of iteration > Speculation.

## 📦 External Data Persistence (CRITICAL)

- Reusable data obtained from API, MCP, connectors, or official web sources MUST be materialized as JSON/NDJSON and registered in `data/input_ledger/snapshot_catalog.ndjson` in the same canonical work line.
- Before fetching the same dataset again, resolve the latest accepted artifact by stable `reuse_key` with `python scripts/snapshot_store.py latest --reuse-key <key>` and reuse it when sufficiently fresh for the task.
- Each accepted snapshot MUST retain source identity, retrieval date/time, query/scope, primary-source URLs, schema version, record count, and artifact SHA-256 according to `data/input_ledger/source_registry.json`.
- Never claim an external dataset is durably "acquired" merely because it existed in chat/tool output. It is reusable only after materialization plus catalog registration (or an explicitly documented alternative canonical store).
- Never fill missing rows or unavailable fields from memory. Preserve unavailable values and fail closed when provenance or artifacts are incomplete.
- Canonical protocol: `docs/specs/external_snapshot_store.md`.

## 🎯 Skill Management

- Sync via `agr sync`.
- Canonical source: `.agent/skills/`.
- Edit **only** in `.agent/skills/`.

---

*Refer to `CLAUDE.md` for specific agent instructions.*
