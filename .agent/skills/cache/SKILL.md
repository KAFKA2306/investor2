---
name: cache
description: Use for reusable external-data retrieval, cache reuse, provenance capture, and snapshot auditing.
origin: local-git-analysis
---

# Reusable External Data

Use the repository's canonical snapshot and input-ledger contracts instead of inventing cache paths, cache schemas, or ad-hoc refresh commands.

## Rules

1. Reuse a sufficiently fresh accepted snapshot before refetching the same dataset.
2. For reusable external data, preserve source identity, operation/query scope, retrieval time, information cutoff, primary-source URLs, schema version, record count, and content hash where required.
3. Keep observed facts, derived values, and assumptions distinct.
4. Do not invent missing values or silently substitute another source when the requested source is unavailable.
5. Materialize reusable results and register them through the canonical snapshot/ledger path when persistence is in scope.
6. Fail closed on missing provenance, missing artifacts, hash mismatch, disabled/unregistered sources, or incompatible schema.

## Canonical commands

```bash
task data:snapshots:audit
task data:snapshots:latest REUSE_KEY=<reuse-key>
```

Use the specific documented acquisition task for a source when a fresh fetch is required, for example `task jquants:fetch:latest` or `task edinet:fetch:all`. Do not assume undocumented aliases such as `data:sync` or `cache:inspect` exist.

## Canonical flow

```text
resolve accepted snapshot
  -> reuse if sufficiently fresh
  -> otherwise fetch from the intended source
  -> normalize without inventing missing values
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
