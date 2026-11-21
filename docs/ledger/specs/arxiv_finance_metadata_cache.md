# arXiv finance metadata cache

## Purpose

ChatGPT / agents should not re-discover a paper universe from ephemeral web searches every time a request such as “implement and validate major 2021 finance papers on arXiv” arrives. `investor2` therefore materializes the discovery universe first, then performs curation, implementation, and empirical validation against that fixed input.

## Canonical split

### GitHub: control plane and small canonical inputs

Keep the following in this repository:

- normalized arXiv descriptive metadata by year;
- exact arXiv query, retrieval timestamp, and source URLs;
- snapshot catalog entry and SHA-256;
- paper-selection manifests and reasons for inclusion/exclusion;
- implementation code, test fixtures, validation protocol, and compact results;
- pointers plus immutable revisions/hashes for any externally stored bulk dataset.

This makes the Pages UI, CI, and ChatGPT/GitHub connector consume the same versioned evidence.

### Hugging Face: optional bulk data plane

Use a Hugging Face Dataset repository only when an input is both materially too large for this Git repository and legally redistributable. GitHub remains authoritative for the manifest: dataset repo ID, revision/commit, file hash, schema, license/provenance, and the validation run that consumed it.

Do not move small paper metadata to Hugging Face merely to introduce another dependency.

### Google Drive

Drive is not a canonical machine-validation store for this pipeline. It may be used as a human working area or private backup, but a validation run must resolve its inputs through the repository snapshot ledger or a revision-pinned external dataset store.

## arXiv acquisition contract

Canonical source: `https://export.arxiv.org/api/query`.

The fetcher uses the eight Quantitative Finance categories that arXiv defines directly:

- `q-fin.CP` Computational Finance
- `q-fin.GN` General Finance
- `q-fin.MF` Mathematical Finance
- `q-fin.PM` Portfolio Management
- `q-fin.PR` Pricing of Securities
- `q-fin.RM` Risk Management
- `q-fin.ST` Statistical Finance
- `q-fin.TR` Trading and Market Microstructure

`q-fin.EC` is deliberately excluded because arXiv defines it as an alias for `econ.GN`; economic-paper discovery can be a separate universe rather than silently broadening a finance request.

The API query fixes `submittedDate` to a UTC calendar year. Pagination is limited to at most 2,000 records per call and consecutive calls are separated by at least three seconds. Parsed records retain the arXiv ID, title, authors, abstract, published/updated timestamps, categories, DOI/journal reference when supplied, and arXiv links.

## Copyright boundary

Only descriptive metadata is cached by this pipeline. arXiv's API terms permit retrieval, storage, transformation, and sharing of descriptive metadata under CC0, while e-print PDFs/source remain subject to the submission's copyright/license. The repository therefore stores links to paper content instead of mirroring PDFs by default.

Primary references:

- https://info.arxiv.org/help/api/user-manual.html
- https://info.arxiv.org/help/api/tou.html
- https://arxiv.org/category_taxonomy

## Run

```bash
python scripts/fetch_arxiv_finance_metadata.py \
  --year 2021 \
  --output docs/research/data/arxiv_qfin_2021.json \
  --register

python tests/test_fetch_arxiv_finance_metadata.py
python scripts/snapshot_store.py audit
```

The resulting snapshot is resolved later with:

```bash
python scripts/snapshot_store.py latest \
  --reuse-key arxiv/q-fin/2021/metadata
```

## From metadata to a validated claim

The metadata snapshot is a discovery universe, not a “major paper” ranking and not evidence that a strategy works. A paper is promoted to implementation only after a separate selection manifest records the criterion used (for example reproducible public code/data, citation/venue evidence, or direct relevance to an investor2 claim). Validation then follows the existing repository rules: frozen trial set, separated selection/final test, point-in-time inputs, trading frictions where relevant, and explicit PASS/FAIL/UNKNOWN evidence.
