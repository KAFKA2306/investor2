---
name: cache
description: Use for reusable external-data retrieval, cache reuse, provenance capture, and snapshot auditing.
origin: local-git-analysis
---

# Reusable External Data

Use the repository's canonical snapshot and input-ledger contracts instead of inventing cache paths, schemas, or refresh commands.

## Rules

1. Reuse a sufficiently fresh accepted snapshot before refetching the same dataset.
2. Preserve source identity, operation/query scope, retrieval time, information cutoff, primary-source URLs, schema version, record count, and content hash where the owning snapshot contract requires them.
3. Materialize reusable results and register them through the canonical snapshot/ledger path when persistence is in scope.
4. Treat a snapshot that fails its provenance, artifact, hash, source-registration, or schema checks as unusable.

## Canonical commands

```bash
task data:snapshots:audit
task data:snapshots:latest REUSE_KEY=<reuse-key>
```

Use the documented acquisition task for a fresh fetch, such as `task jquants:fetch:latest` or `task edinet:fetch:all`.

## Canonical flow

```text
resolve accepted snapshot
  -> reuse if sufficiently fresh
  -> otherwise fetch from the intended source
  -> materialize reusable data
  -> register provenance + hash
  -> audit
  -> consume registered artifact
```

## Canonical references

- `docs/specs/external_snapshot_store.md`
- `data/input_ledger/`
- `Taskfile.yml`
- `AGENTS.md`
