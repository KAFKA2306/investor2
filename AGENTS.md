# Investor2 Agent Contract

`AGENTS.md` is the only repository-wide agent instruction source. Canonical skills live in `.agent/skills/`.

## Purpose

This repository owns investment hypotheses, point-in-time evidence, out-of-sample validation, and decision records. Optimize decision quality and reproducibility rather than activity volume.

Prefer current primary data, exact source identity and timestamps, canonical repository state, and direct measurements. Never infer unavailable values, dates, provenance, model results, or success.

For persisted external data, preserve the source, retrieval time, query/scope, primary URL, schema/version, record count, and hash when the owning contract requires them.

A backtest alone is not acceptance evidence. Respect point-in-time data, OOS evaluation, baseline, ablation, costs, reproducibility, and applicable portfolio metrics. A failed hypothesis is a valid result.

## Execution

- Proceed with read-only and reversible work without unnecessary confirmation.
- Reuse the existing Taskfile surface instead of adding wrappers.
- Reuse one canonical ledger/pipeline/config/workline for each outcome.
- Use `DELETE > MERGE > REPLACE > ADD`.
- Fail closed on missing provenance/schema/artifacts.
- Do not substitute mocks, dummy values, cached examples, or silent fallback for acceptance-critical production data.

## Verification

Run the narrowest relevant verifier first. `task check` is the repository-level gate unless a narrower documented check fully proves the changed contract.

A PR may merge when the reviewed revision satisfies repository-local acceptance criteria. Release is separate: datasets, models, dashboards, or public surfaces require the actual merged artifact/surface to be directly verified.

CI success does not prove deployment. Merge does not prove release.

## Completion

Reuse an existing Issue/PR for the same decision. If work remains, leave one exact falsifiable next action there. Stop when the requested decision/repository/release state is directly verified.
