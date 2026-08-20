# BLS labor productivity data

This repository stores the U.S. Bureau of Labor Statistics (BLS) Nonfarm Business sector annual labor-productivity history as a reproducible, content-addressed snapshot.

## Official source

The collector uses the BLS Productivity and Costs (`pr`) time-series flat files directly:

- `https://download.bls.gov/pub/time.series/pr/pr.series`
- `https://download.bls.gov/pub/time.series/pr/pr.sector`
- `https://download.bls.gov/pub/time.series/pr/pr.measure`
- `https://download.bls.gov/pub/time.series/pr/pr.duration`
- `https://download.bls.gov/pub/time.series/pr/pr.period`
- `https://download.bls.gov/pub/time.series/pr/pr.data.1.AllData`

The BLS release documentation states that full historical annual and quarterly productivity measures include percent changes and indexes. The current source metadata identifies:

- sector: `Nonfarm Business` (`8500`)
- measure: `Labor productivity (output per hour)` (`09`)
- annual period: `Annual Average` (`Q05`)
- annual percent-change series: `PRS85006091`
- index series: `PRS85006093`, currently `2017=100`

The collector resolves those identifiers from the BLS metadata files rather than relying on the numeric codes alone. If the metadata no longer maps uniquely, collection fails instead of silently selecting another series.

## Repository outputs

- `data/bls_labor_productivity/latest.json`: current normalized history for consumers.
- `data/snapshots/bls_labor_productivity/`: immutable content-addressed accepted snapshots.
- `data/input_ledger/snapshot_catalog.ndjson`: SHA-256, observation time, source URLs, schema version, and provenance for every accepted changed snapshot.

The normalized record schema is:

```json
{
  "year": 2025,
  "percent_change": 2.1,
  "index": 117.785
}
```

No missing values are interpolated. The percent-change history must be contiguous, and every percent-change year must have an official BLS index value. The historical contract begins in 1948. A source change that violates those checks fails closed.

## Continuous collection

`.github/workflows/bls-labor-productivity.yml` runs on weekdays at `14:47 UTC`, after the BLS Productivity and Costs scheduled `08:30 ET` release time in both daylight and standard time. It can also be run manually.

Each run downloads the current official flat files and rebuilds the complete annual history. A new snapshot and ledger entry are committed only when the normalized BLS content changes. Historical revisions therefore remain recoverable through the content-addressed snapshot path and Git history without creating duplicate commits when BLS data is unchanged.

The workflow requires no API key.
