# Spark + Iceberg research projection

This workline adds a disposable analytical projection over investor2's canonical research evidence.

Canonical JSON/NDJSON files remain authoritative. Spark reads them; Iceberg stores queryable copies for cross-run analysis. Nothing writes facts back into the canonical ledgers.
