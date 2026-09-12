---
name: fred-economic-data
description: Use only when a task needs FRED macro data through investor2's implemented macro-ingestion path.
origin: local-git-analysis
---

# FRED Economic Data

Use `src/io/sync_macro.ts` through the repository data-acquisition flow in `src/io/get.ts`, with `.agent/skills/cache/SKILL.md` for snapshot reuse and provenance.

Read `FRED_API_KEY` from the environment. Preserve observation dates and retrieval metadata. For historical backtests, distinguish currently published revised observations from genuinely point-in-time vintage data.

Treat the series implemented in `src/io/sync_macro.ts` as the supported set. For any other FRED series, release-calendar use, or ALFRED vintage, add and verify an explicit source path under the repository provenance contract before using it as evidence.

## References

- `src/io/sync_macro.ts`
- `src/io/get.ts`
- `.agent/skills/cache/SKILL.md`
- `docs/specs/external_snapshot_store.md`
- `AGENTS.md`
