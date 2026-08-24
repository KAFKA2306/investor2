---
name: edinet
description: Retrieve EDINET filings and build point-in-time Japanese equity datasets. Use for filing acquisition, XBRL/text extraction, period alignment, provenance, corporate-action handling, and PIT-clean backtest inputs.
origin: local
---

# EDINET

Use the repository's existing EDINET entry points and canonical evidence paths rather than creating a second ingestion or dataset pipeline.

## Contract

- Preserve document identity, submission time, accounting period, source URL or EDINET document ID, and retrieval metadata.
- A value becomes usable only when it was publicly available at the evaluation timestamp; never backfill future filings into earlier observations.
- Keep annual, quarterly, amended, and extraordinary filings distinguishable when aligning periods.
- Preserve corporate-action adjustments and transformation metadata instead of silently rewriting historical values.
- Treat missing, malformed, late, or conflicting filings as explicit data-quality states; do not interpolate unless the research protocol defines and tests that rule.
- Reuse accepted cached/snapshotted filings when sufficiently fresh; otherwise acquire through the canonical repository path.
- Emit datasets with provenance and reproducible transformation parameters suitable for frozen OOS evaluation.

## Verification

Check the resulting observation timestamps, source identifiers, row counts, duplicate keys, amendment handling, and a sample of cross-period joins before using the dataset in research.
