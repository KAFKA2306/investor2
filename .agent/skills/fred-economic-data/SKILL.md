---
name: fred-economic-data
description: Use for FRED-backed macro data already supported by this repository, including policy rates, Treasury yields, CPI, unemployment, and inflation expectations.
origin: local-git-analysis
---

# FRED Economic Data

Use the repository's existing macro ingestion path.

## Current implementation

`src/io/sync_macro.ts` reads `FRED_API_KEY` and fetches these FRED series through the shared HTTP cache:

- `FEDFUNDS`
- `DGS10`
- `CPIAUCSL`
- `UNRATE`
- `T10YIE`

`src/io/get.ts` invokes `syncMacro()` as part of the repository data-acquisition flow.

## Contract

- Read `FRED_API_KEY` from the environment.
- Use the repository macro ingestion path and shared snapshot/cache contract.
- Preserve observation dates and retrieval metadata.
- For historical backtests, distinguish currently published revised values from genuinely point-in-time vintage data.
- Do not claim support for arbitrary FRED series, release calendars, or ALFRED vintages unless the corresponding implementation exists and is verified.
- For a series outside the implemented set, add an explicit source path under the repository provenance contract before using it as evidence.

## Canonical references

- `src/io/sync_macro.ts`
- `src/io/get.ts`
- `.agent/skills/cache/SKILL.md`
- `docs/specs/external_snapshot_store.md`
- `AGENTS.md`
