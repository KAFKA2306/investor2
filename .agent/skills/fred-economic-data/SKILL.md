---
name: fred-economic-data
description: Use for FRED-backed macro data already supported by this repository, including policy rates, Treasury yields, CPI, unemployment, and inflation expectations.
origin: local-git-analysis
---

# FRED Economic Data

Use the repository's existing macro ingestion path. Do not invent a separate FRED client, generic query layer, or economic-calendar subsystem.

## Current implementation

`src/io/sync_macro.ts` reads `FRED_API_KEY` and fetches these FRED series through the shared HTTP cache:

- `FEDFUNDS`
- `DGS10`
- `CPIAUCSL`
- `UNRATE`
- `T10YIE`

`src/io/get.ts` invokes `syncMacro()` as part of the repository data-acquisition flow.

This is the currently implemented surface. There is no repository `FREDQuery` class and no generic arbitrary-series API wrapper documented as canonical.

## Contract

- Never hard-code credentials; read `FRED_API_KEY` from the environment.
- Reuse the repository HTTP cache and snapshot/provenance contract rather than bypassing it with ad-hoc requests.
- Preserve observation dates and retrieval metadata.
- Treat missing or malformed observations as explicit data-quality states; do not invent or interpolate values unless a frozen research protocol defines that transformation.
- For historical backtests, distinguish currently published revised values from genuinely point-in-time vintage data. Do not call revised series PIT-clean without vintage evidence.
- Do not claim support for arbitrary FRED series, release calendars, or ALFRED vintages unless the corresponding implementation is added and verified.
- If a requested macro series is outside the implemented set, report the gap or add a new explicit source path under the repository's provenance contract before using it as evidence.

## Canonical references

- `src/io/sync_macro.ts`
- `src/io/get.ts`
- `.agent/skills/cache/SKILL.md`
- `docs/specs/external_snapshot_store.md`
- `AGENTS.md`
