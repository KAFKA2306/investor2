---
name: edinet
description: Retrieve EDINET filings and build point-in-time Japanese equity inputs.
origin: local
---

# EDINET

Use this skill for EDINET filing acquisition, period alignment, and PIT dataset construction.

Preserve document identity, submission time, accounting period, EDINET document ID/source, and amendment type. An observation may enter a historical evaluation only after its public submission time.

Keep annual, quarterly, amended, and extraordinary filings distinguishable. Preserve corporate-action adjustment metadata when transformations are applied.

Before research use, verify observation timestamps, source identifiers, duplicate keys, amendment handling, row counts, and representative cross-period joins.

Use the current EDINET repository entry points and snapshot path rather than creating another ingestion pipeline.
