# Spark + Iceberg research projection

This is a disposable analytical projection over investor2's canonical research evidence.

```text
canonical JSON / NDJSON
  ├─ data/input_ledger/snapshot_catalog.ndjson
  ├─ data/hypothesis_lab/hypotheses/*.json
  ├─ docs/research/results/**/summary.json
  └─ data/benchmarks/*.json
          ↓
       Spark 4.1.3
          ↓
      Iceberg 1.12.0
          ├─ research.evidence.input_snapshots
          ├─ research.evidence.hypotheses
          ├─ research.evidence.oos_results
          └─ research.evidence.benchmark_contracts
```

## Authority boundary

The JSON/NDJSON files above remain canonical. Iceberg is derived state for cross-run analysis only.

The projection:

- never writes facts back to the canonical ledgers
- preserves raw JSON and source hashes for hypotheses, OOS results, and benchmark contracts
- expands legacy concatenated OOS JSON objects into individually identified projection rows
- normalizes top-level and nested research outcome status into one queryable verdict column
- preserves snapshot provenance as canonical JSON text
- runs the canonical snapshot-store audit before projection and fails closed on missing/mutated/provenance-invalid evidence
- fails closed on duplicate snapshot point-in-time coordinates or non-accepted snapshot status
- requires exact row/key parity after Iceberg read-back
- requires Iceberg snapshot metadata for every table

No managed lakehouse, object-storage account, or paid API is required.

## Run

```bash
task analytics:check
```

Equivalent Docker command:

```bash
docker compose -f compose.analytics.yaml run --rm spark
docker compose -f compose.analytics.yaml down -v
```

The success marker is:

```text
RESEARCH_PROJECTION_OK
```

The warehouse is a Docker volume and is intentionally disposable. Rebuild it from canonical repository evidence whenever needed.
