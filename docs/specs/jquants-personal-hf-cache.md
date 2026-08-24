# J-Quants owner-only private cache

## Purpose

Avoid repeating multi-hour J-Quants Free acquisition when the same historical rows are reused for personal analysis.

This cache is distinct from external/public data publication. It is a **Private Hugging Face Dataset used only by the J-Quants account owner**.

Canonical Dataset:

`k4fka/investor2-jquants-free-cache`

Canonical implementation:

- `scripts/jquants_private_hf_cache.py`
- `.github/workflows/jquants-personal-hf-cache.yml`

## J-Quants usage boundary

The current J-Quants FAQ describes the individual service as limited to private personal use and prohibits third-party distribution or sharing of acquired data in a viewable form. This repository therefore distinguishes two storage modes:

1. **Owner-only private cache:** personal storage used only by the account owner. Allowed by this repository contract while the Dataset remains Private and unshared.
2. **External/shared publication:** any public Dataset, collaborator/shared access, downstream application, or third-party distribution. This remains blocked unless the required J-Quants permission/license is separately established.

If the private Dataset is ever made public or shared with another person/account, stop using this contract and re-evaluate the license boundary before continuing.

This is an engineering interpretation of the published J-Quants usage boundary, not legal advice.

## Storage contract

```text
J-Quants API v2
  ↓ only for cache misses
GitHub Actions runner plaintext working copy
  ↓ client-side AES-256-GCM
Private HF Dataset owned by the same user
  personal-cache/v1/daily/YYYY/MM/YYYY-MM-DD.bin.enc
  ↓
cache-only materialization
  ↓ decrypt on runner
hash / row-count / date-range verification
  ↓
research input
```

Rules:

- Dataset visibility must be `private`.
- Do not add collaborators or otherwise share the Dataset.
- No plaintext J-Quants rows are uploaded to Hugging Face.
- Each weekday has an immutable encrypted shard, including an encrypted empty marker for holidays/non-market weekdays.
- Existing shards are reused; only missing weekdays may call J-Quants.
- Plaintext working data is deleted from the runner with an `always()` cleanup step.
- No raw J-Quants rows are committed to GitHub or uploaded as GitHub Actions artifacts.

## Encryption

Each shard uses AES-256-GCM.

The cache key is derived as:

```text
SHA-256("investor2-jquants-personal-hf-cache-v1\\0" || JQUANTS_API_KEY)
```

The API key and derived key are never written to the Dataset, manifests, logs, repository, or artifacts.

Operational consequence: if the J-Quants API key must be rotated, the existing cache must be re-encrypted or otherwise migrated before the old key becomes unavailable.

## Cache semantics

The Free window is resolved from the run date using the current two-year history / twelve-week delay contract. The implementation enumerates weekdays in that window.

For every expected weekday:

- cached shard exists → decrypt and reuse; no J-Quants call;
- cached shard absent → fetch that date once, encrypt the result or empty-day marker, upload to the private cache.

The cache is append-only by date. When the rolling Free window advances, prior dates remain available for other personal research while only newly visible weekdays need acquisition.

## Required proof

A cache implementation is not considered complete because upload succeeded.

The live acceptance run must:

1. seed/increment the current Free window;
2. delete the first plaintext materialization;
3. materialize the same window again from the private HF cache with `--require-cache-complete`;
4. prove `request_count == 0` on the second pass;
5. prove identical date range, row count, ticker count, observed market days and materialized file hashes;
6. prove the HF repository is still Private and the manifest declares no plaintext J-Quants rows on HF.

Only after this round trip passes should research workflows switch from full reacquisition to the personal cache.

## External publication remains separate

`docs/specs/jquants-hf-pipeline.md` and `.github/workflows/jquants-hf-publish.yml` govern shared/external publication. Their distribution authorization gate is not removed by this personal-cache contract.
