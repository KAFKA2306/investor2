# BLS labor productivity data

This repository stores the U.S. Bureau of Labor Statistics (BLS) Nonfarm Business sector annual labor-productivity history as reproducible, content-addressed snapshots.

## Official source

Continuous collection uses the historical workbook that BLS links from the current Productivity and Costs release for full historical annual and quarterly measures:

- `https://www.bls.gov/web/prod2/labor-productivity-major-sectors.xlsx`
- tables index: `https://www.bls.gov/productivity/tables/home.htm`
- current release: `https://www.bls.gov/news.release/prod2.htm`

The collector reads the workbook's `MachineReadable` sheet directly. No annual values are recomputed from quarterly observations.

The current workbook identifies the selected rows as:

- sector: `Nonfarm business sector`
- basis: `All workers`
- measure: `Labor productivity`
- annual period: `Annual`
- annual change: `% Change from previous year`
- index: currently `Index (2017=100)`

The collector discovers the index definition from the workbook rather than hard-coding the base year. A changed workbook header, multiple index definitions, duplicate year, missing annual year, incomplete index coverage, malformed XLSX structure, or stale history causes collection to fail rather than synthesize data.

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

No missing values are interpolated. The annual percent-change history must remain contiguous from 1948, and every percent-change year must have an official BLS index observation.

## Continuous collection

`.github/workflows/bls-labor-productivity.yml` runs on weekdays at `14:47 UTC`, after the scheduled `08:30 ET` Productivity and Costs release time in both daylight and standard time. It can also be run manually.

Each run downloads the current official workbook, checks that it is an XLSX archive, parses the `MachineReadable` sheet with the Python standard library, and reconstructs the deterministic normalized snapshot. A new content-addressed snapshot and ledger entry are committed only when the normalized BLS data changes. Historical BLS revisions therefore remain recoverable through immutable snapshot paths and Git history, while unchanged polling produces no data commit.

The workflow requires no API key, repository secret, or third-party data provider.
