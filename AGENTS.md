# Investor2 Agent Contract

`AGENTS.md` is the repository-wide instruction source. Canonical task-specific skills live in `.agent/skills/`.

## Scope

This repository owns investment hypotheses, point-in-time evidence, out-of-sample validation, and decision records. Optimize decision quality and reproducibility rather than activity volume.

Use current primary data, exact source identity and timestamps, canonical repository state, and direct measurements. Do not infer unavailable values, dates, provenance, model results, or success.

For persisted external data, preserve the provenance fields required by the owning snapshot contract, including source, retrieval time, query/scope, primary URL, schema/version, record count, and hash.

## Research invariants

- A backtest alone is not acceptance evidence. Respect point-in-time data, untouched OOS evaluation, baseline, ablation, costs, reproducibility, and applicable portfolio metrics.
- A failed hypothesis is a valid result.
- Fail closed on missing acceptance-critical provenance, schema, or artifacts.
- Do not substitute mocks, dummy values, cached examples, or silent fallback for acceptance-critical production data.

## Canonical execution

Reuse the existing `Taskfile.yml` surface and canonical ledger/pipeline/config for the outcome. `task check` is the repository-level gate unless a narrower documented verifier fully proves the changed contract.

## Release boundary

Repository checks prove only the exact revision they executed. Dataset, model, dashboard, or public release requires direct verification of the actual merged artifact or surface. CI success does not prove deployment, and merge does not prove release.
