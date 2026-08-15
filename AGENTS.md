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

## 🧭 Agent Goal Contract

The repository goal is not to maximize Issues closed, experiments run, datasets fetched, or lines changed. The goal is to improve investment decisions and make future evidence acquisition/analysis cheaper and more reliable.

For every non-trivial workline define:

- **Decision** — what investment/research decision this work can improve;
- **Uncertainty** — the specific unknown or ambiguity that currently limits that decision;
- **Evidence Test** — the smallest falsifiable observation/experiment that can reduce the uncertainty;
- **Capability Delta** — what reusable capability remains after this run so the same class of decision is cheaper, faster, safer, or more reproducible next time;
- **Acceptance Criteria** — deterministic conditions that prove the requested outcome;
- **Stopping Condition** — the fixed point after which further work is a separate decision problem.

If no decision, uncertainty reduction, or reusable capability can be stated, do not expand the work merely because an Issue exists.

## 🔁 Goal-Driven Execution Loop

For multi-step research or engineering work, keep one Goal active and iterate:

```text
inspect current evidence/state
  -> define smallest falsifiable next step
  -> implement or acquire evidence
  -> run the cheapest relevant verifier
  -> inspect result
  -> repair/revise if falsified
  -> persist reusable evidence/capability
  -> stop at the fixed point
```

A failed experiment, source fetch, schema check, or test is evidence. Preserve the failure reason needed to improve the next step; do not relabel it as success or hide it behind a later summary.

Prefer the cheapest sufficient next action. Do not repeatedly fetch, search, or recompute when a current accepted snapshot, deterministic artifact, or prior exact result already answers the same question.

## 🧠 Durable Continuation

Before starting a Goal:

1. inspect current `main`, relevant Issues, open PRs, branches, CI, existing snapshots, and prior accepted artifacts;
2. continue the existing canonical workline when it already represents the same Decision/Uncertainty;
3. otherwise create one bounded workline;
4. do not create parallel datasets, duplicate ledgers, replacement branches, or alternate pipelines for the same outcome.

When work cannot finish, leave it resumable through existing canonical surfaces rather than chat memory. Record as applicable in the owning Issue/PR and existing ledgers/artifacts:

- last verified revision;
- Decision and remaining Uncertainty;
- evidence already acquired and its stable location/hash;
- failing stage or blocker;
- exact next falsifiable action.

Do not invent a second agent-state database when the canonical Issue/PR, snapshot catalog, artifact, or repository state already carries the continuation information.

## ✅ Evidence-Driven Completion

Do not equate activity with completion.

A task is complete only when the owning postcondition is inspected. Examples include:

- a reusable external dataset is materialized and registered, not merely fetched;
- a research result is reproducible from versioned inputs and code, not merely described;
- a decision metric is produced with explicit period/unit/source semantics, not merely calculated once in chat;
- a code change passes the relevant deterministic checks on the reviewed revision;
- a public/deployed result is read back when publication itself is in scope.

Treat material claims as:

- **VERIFIED** — directly supported by current primary/repository/test/artifact/CI evidence;
- **OBSERVED** — explicitly supplied observation;
- **INFERRED** — derived from evidence and reported as inference;
- **UNVERIFIED** — not inspected and never stated as fact;
- **FABRICATED** — forbidden.

## 🧪 Builder / Auditor Separation

Treat implementation and acceptance as separate phases even when one agent performs both sequentially.

### Builder

May acquire evidence and modify code, schemas, tests, data projections, research outputs, dashboards, docs, and workflows within the bounded Goal Contract.

### Auditor

Independently verifies:

- the Decision/Uncertainty actually addressed by the work;
- source identity, period, units, vintage, and provenance;
- persisted artifacts and snapshot registration where required;
- deterministic checks on the relevant commit/revision;
- result/claim boundaries and whether stronger conclusions exceed the evidence;
- Capability Delta is real and reusable rather than prose-only;
- no duplicate workline or task-created residue remains.

Implementation intent is never acceptance evidence.

## 🏁 Fixed Point

Stop when all are true:

- the requested Decision/Outcome is materially improved or the bounded evidence test has reached a truthful negative result;
- remaining uncertainty is explicitly known rather than silently guessed away;
- required evidence is persisted in the canonical repository surface;
- relevant `task check` / focused tests / audits pass, or the exact blocker is recorded;
- exact-head CI is verified when applicable;
- the Capability Delta is usable by a future run without rediscovering the same evidence/process;
- owning Issue/PR state is correct;
- temporary files, duplicate branches/PRs, and superseded helper paths created by the task are removed;
- additional ideas no longer change the current Decision/Acceptance Criteria and therefore belong to a separate Goal.

At the fixed point, stop. Do not turn a completed Decision into an unbounded refactor or research sweep.

## 📣 Final Report Contract

Report verified outcome rather than tool activity. Include as applicable:

- Decision and uncertainty reduced;
- evidence/experiment result;
- Capability Delta left behind;
- Issue/PR/commit or stable artifact location;
- tests/audits/exact-head CI result;
- remaining blocker and exact next action if unfinished.

---

*Refer to `CLAUDE.md` for specific agent instructions.*
