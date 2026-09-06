---
name: fred-economic-data
description: Use the repository's implemented FRED macro series and ingestion path.
origin: local-git-analysis
---

# FRED Economic Data

The implemented path is `src/io/sync_macro.ts`, invoked through `src/io/get.ts`.

Current supported series:

- `FEDFUNDS`
- `DGS10`
- `CPIAUCSL`
- `UNRATE`
- `T10YIE`

Read `FRED_API_KEY` from the environment and use the repository HTTP cache/snapshot path.

For historical evaluation, distinguish revised FRED observations from genuine vintage data. Treat a series as PIT-clean only when vintage evidence supports that claim.

A request for another FRED series or ALFRED vintage requires an explicit implemented source path before research use.
