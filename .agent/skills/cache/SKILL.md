---
name: cache
description: Use when reusing, refreshing, or auditing an external-data snapshot registered by investor2.
origin: local-git-analysis
---

# Reusable External Data

Use the repository's canonical snapshot and input-ledger path. Do not invent cache locations, schemas, or refresh commands.

Before fetching, resolve an accepted snapshot for the same dataset and reuse it when it satisfies the owning freshness contract. Otherwise use the existing acquisition task, register the result with the required provenance and hash, then audit it before consumption.

A snapshot that fails its provenance, artifact, hash, source-registration, or schema checks is unusable.

## Commands

```bash
task data:snapshots:latest REUSE_KEY=<reuse-key>
task data:snapshots:audit
```

Fresh acquisition uses the existing source-specific Taskfile command.

## References

- `docs/specs/external_snapshot_store.md`
- `data/input_ledger/`
- `Taskfile.yml`
- `AGENTS.md`
