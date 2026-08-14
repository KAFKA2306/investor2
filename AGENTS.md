# Repository Guidelines (Slim Mode)

## 📍 Key Locations

- **Commands**: `src/commands/`
- **I/O**: `src/io/`
- **Research**: `src/research/`
- **ADRs**: `docs/adr/`

## ⚙️ Core Operational Commands

- `task setup`: Install locked Bun/Python dependencies and install the local `prek` hook.
- `task check`: Non-mutating reliability gate: format check + lint + type check + tests + external snapshot audit.
- `task run:newalphasearch`: Alpha discovery pipeline.
- `task dashboard:dev`: Start the dashboard server.

## 🛡️ Governance (CRITICAL)

- **CDD (Crash-Driven Development)**: NO `try-catch`, NO defensive code. Let it crash, fix the root cause.
- **Deterministic Quality**: Biome owns TS formatting/import organization; Oxlint owns TS lint; `tsc --noEmit` owns TS types. Ruff owns Python format/lint; Pyrefly owns Python types. `prek` calls the same fast gates locally.
- **Schema-First**: Use Zod (TS) or Pydantic (Py) at real untrusted/runtime boundaries; do not duplicate trusted internal types only to add validation.
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
