---
name: cache
description: Use for reusable external-data snapshot lookup, refresh, and provenance registration.
origin: local-git-analysis
---

# Reusable External Data

Use the repository snapshot store before fetching a reusable external dataset again.

## Flow

1. Resolve the newest accepted snapshot for the reuse key.
2. Reuse it when it satisfies the caller's freshness requirement.
3. Otherwise fetch through the source-specific repository path.
4. Materialize the result and register its provenance and content hash.
5. Audit the snapshot store before consumption.

## Commands

```bash
task data:snapshots:latest REUSE_KEY=<reuse-key>
task data:snapshots:audit
```

Source-specific acquisition commands remain in `Taskfile.yml`.

## Reference

- `docs/specs/external_snapshot_store.md`
- `data/input_ledger/`
