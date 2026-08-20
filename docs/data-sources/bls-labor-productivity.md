# BLS labor productivity data

This repository stores the U.S. Bureau of Labor Statistics (BLS) Nonfarm Business sector annual labor-productivity history as reproducible, content-addressed snapshots.

## Official source

Continuous collection uses the BLS Public Data API version 1:

- `https://api.bls.gov/publicAPI/v1/timeseries/data/`
- API documentation: `https://www.bls.gov/developers/home.htm`
- API limits and behavior: `https://www.bls.gov/developers/api_faqs.htm`

BLS documents version 1 as open for public use without registration. Unregistered requests are limited to 25 queries per day, 25 series per query, and 10 years per query. The current 1948-to-present collection therefore requests both required series together in eight non-overlapping windows. BLS also documents a one-day lag between published data and availability through the API.

The API does not return series metadata. The series contract was therefore verified on 2026-08-21 against the official BLS Productivity and Costs (`pr`) metadata files:

- `https://download.bls.gov/pub/time.series/pr/pr.series`
- `https://download.bls.gov/pub/time.series/pr/pr.sector`
- `https://download.bls.gov/pub/time.series/pr/pr.measure`
- `https://download.bls.gov/pub/time.series/pr/pr.duration`
- `https://download.bls.gov/pub/time.series/pr/pr.period`

That metadata identifies:

- sector: `Nonfarm Business` (`8500`)
- measure: `Labor productivity (output per hour)` (`09`)
- annual period: `Annual Average` (`Q05`)
- annual percent-change series: `PRS85006091`
- index series: `PRS85006093`; the metadata verified on 2026-08-21 labels it `Index (2017=100)`

The collector pins the two official series IDs and does not infer replacements. A missing series, missing annual year, duplicate year, incomplete index coverage, malformed API response, or stale history causes collection to fail rather than synthesize data.

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

`.github/workflows/bls-labor-productivity.yml` runs every day at `14:47 UTC` and can also be run manually. Daily execution is intentional because the unregistered API is documented as lagging published releases by one day; a weekend run can therefore capture a Friday release as soon as it becomes available through the API.

Each run requests the complete official history, normalizes only `Q05` annual observations, and reconstructs the deterministic snapshot. A new content-addressed snapshot and ledger entry are committed only when the normalized BLS content changes. Historical BLS revisions therefore remain recoverable through immutable snapshot paths and Git history, while unchanged polling produces no data commit.

The workflow requires no API key or repository secret.
