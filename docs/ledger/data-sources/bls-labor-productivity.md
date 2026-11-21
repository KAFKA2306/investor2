# BLS labor productivity data

This repository verifies and stores the U.S. Bureau of Labor Statistics (BLS) Nonfarm Business sector annual labor-productivity history from official BLS Series Report output.

## Official source

The collector uses the BLS Series Report output for two official Productivity and Costs series:

- `PRS85006091`: Nonfarm Business labor productivity, percent change from the same quarter one year ago.
- `PRS85006093`: Nonfarm Business labor productivity, index.

Official surfaces retained as provenance are:

- `https://data.bls.gov/timeseries/PRS85006091`
- `https://data.bls.gov/timeseries/PRS85006093`
- `https://data.bls.gov/pdq/SurveyOutputServlet`
- `https://www.bls.gov/productivity/tables/home.htm`
- `https://www.bls.gov/news.release/prod2.htm`

The workflow asks BLS for the full 1948-present Series Report with annual averages enabled. The parser validates the returned Series Id, sector, measure, table header, annual row identity, numeric values, matching year coverage between the two series, and contiguous history. The current incomplete calendar year may legitimately have no annual average yet and is not synthesized.

## Repository outputs

- `data/bls_labor_productivity/latest.json`: current normalized history for repository consumers.
- `data/snapshots/bls_labor_productivity/`: immutable content-addressed normalized snapshots.
- `data/input_ledger/snapshot_catalog.ndjson`: accepted snapshot SHA-256, retrieval time, source URLs, schema version, record count, and query scope.

Each normalized record has this shape:

```json
{
  "year": 2025,
  "percent_change": 2.1,
  "index": 117.785
}
```

No missing annual values are interpolated. The accepted history must start in 1948, remain contiguous, and contain matching percent-change and index years.

## Collection and validation

`.github/workflows/bls-labor-productivity.yml` performs a live BLS retrieval on relevant pull requests, on relevant pushes to `main`, on weekday schedules, and on manual dispatch.

Pull requests run focused regression tests and parse the live official Series Report into temporary files only. They do not mutate canonical data.

Non-pull-request runs materialize the normalized history into the repository. If the normalized content is unchanged, no snapshot or ledger entry is created. If it changes, the workflow creates a new content-addressed snapshot, registers it through the existing `scripts/snapshot_store.py` catalog using official-source provenance, audits the catalog, updates `latest.json`, and commits only those canonical data changes.

The collector uses only the Python standard library plus `curl` available on the GitHub-hosted runner. It requires no API key, repository secret, third-party market-data provider, or additional data store.
