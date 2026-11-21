# J-Quants → Hugging Face canonical pipeline

## Purpose

`KAFKA2306/investor2` owns the deterministic acquisition and validation boundary for J-Quants API v2. The workflow uses GitHub Actions for execution and Hugging Face Trusted Publishers/OIDC for publication only when external distribution is separately authorized.

Canonical workflow: `.github/workflows/jquants-hf-publish.yml`

## Official constraints

- J-Quants API v2 uses an API key. The official Python client is `J-Quants/jquants-api-client-python` and exposes `ClientV2` wrappers for listed-issue master, daily equity bars, and financial summary data.
- J-Quants' official FAQ states that the individual service is for private use and prohibits third-party distribution of acquired data and provision of applications using the data, whether commercial or non-commercial. Its current product FAQ also states that distributing or sharing acquired data in a viewable format is prohibited. Separate permission/licensing is therefore required before this pipeline may upload J-Quants records to Hugging Face.
- Hugging Face Trusted Publishers allow GitHub Actions to obtain a short-lived repository-scoped token through OIDC instead of storing a long-lived `HF_TOKEN`. Hugging Face recommends constraining the trusted publisher by repository, branch, and workflow.

Primary sources:

- https://github.com/J-Quants/jquants-api-client-python
- https://jpx-jquants.com/
- https://pro.jpx-jquants.com/termsofservice
- https://huggingface.co/docs/hub/en/trusted-publishers

## Data flow

```text
J-Quants API v2
  ↓  JQUANTS_API_KEY
GitHub Actions ephemeral runner
  ↓
fetch narrow date window
  ↓
validate required columns / keys / latest market date
  ↓
.jquants-staging/               (never committed, never uploaded as a GitHub artifact)
  ↓
license gate
  ├─ blocked (default) → delete staging data
  └─ explicitly authorized → Hugging Face OIDC → target Dataset → delete staging data
```

The workflow does not commit J-Quants records to this public repository and does not use `actions/upload-artifact` for them.

## Acquisition contract

`scripts/jquants_hf_pipeline.py` uses the official `ClientV2` methods:

- `get_eq_bars_daily(from_yyyymmdd=..., to_yyyymmdd=...)`
- `get_eq_master(date=...)`
- `get_fin_summary_cursor(date_yyyymmdd=...)`

The daily-bar request uses a narrow calendar window rather than a broad `_range` helper. The latest market date present in that response becomes the canonical snapshot date; weekends and ordinary market holidays therefore do not need hard-coded calendars.

The current validation gate requires:

- daily bars: non-empty `Code`, `Date`; uniqueness on (`Code`, `Date`)
- issue master: non-empty `Code`; uniqueness on `Code`
- financial summary: `Code`, `DiscDate` when rows exist; zero disclosures for a market date is valid

Any contract violation fails the run before publication.

## GitHub configuration

Required secret:

- `JQUANTS_API_KEY`: API key issued by the J-Quants dashboard.

Repository variables:

- `JQUANTS_CANONICAL_SYNC_ENABLED`: set to `true` to enable scheduled live runs. Without it, scheduled runs are skipped; `workflow_dispatch` remains available.
- `JQUANTS_DATA_DELAY_DAYS`: number of calendar days subtracted from today for scheduled acquisition. Default `0`. A plan with delayed data must set this to a suitable value for that plan.
- `HF_DATASET_REPO`: Hugging Face dataset repository ID such as `owner/repository`. Required only after external distribution is authorized.
- `JQUANTS_EXTERNAL_DISTRIBUTION_ALLOWED`: **leave unset/false by default**. Set to `true` only when the account has separate permission or a license that covers the intended external distribution.

No GitHub `HF_TOKEN` secret is required.

## Hugging Face one-time configuration

Only after external distribution is authorized:

1. Create or select the destination Dataset repository.
2. In that Dataset's settings, add a GitHub Actions Trusted Publisher.
3. Constrain it to:
   - repository: `KAFKA2306/investor2`
   - branch: `main`
   - workflow: `jquants-hf-publish.yml`
4. Set `HF_DATASET_REPO` in GitHub repository variables.
5. Set `JQUANTS_EXTERNAL_DISTRIBUTION_ALLOWED=true` only after the J-Quants distribution right is established.

The workflow requests `permissions: id-token: write` and sets `HF_OIDC_RESOURCE=datasets/<HF_DATASET_REPO>` for `hf upload`.

## Run modes

### Pull request / push contract CI

Only Ruff and the deterministic unit tests run. No API key is used and no J-Quants data is fetched.

### Manual live run

Use `workflow_dispatch`. `end_date` may be supplied explicitly; otherwise the workflow resolves today minus `JQUANTS_DATA_DELAY_DAYS`. `lookback_days` defaults to 7.

### Scheduled live run

The workflow is scheduled on weekdays at `11:00 UTC` (`20:00 JST`), but the live job executes only when `JQUANTS_CANONICAL_SYNC_ENABLED=true`.

## Security and retention

- The API key is read only from `secrets.JQUANTS_API_KEY`.
- The key is not written to the manifest or output files.
- J-Quants records stay in `.jquants-staging` on the ephemeral runner.
- The staging directory is deleted with `if: always()` whether validation, publication, or a later step succeeds or fails.
- No long-lived Hugging Face token is stored in GitHub.
