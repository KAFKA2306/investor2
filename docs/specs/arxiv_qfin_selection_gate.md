# arXiv q-fin selection gate

## Purpose

The 2021 arXiv Quantitative Finance snapshot is a discovery universe, not a ranked list of major papers and not evidence that any strategy works. This gate reduces that fixed universe to a deterministic paper-inspection queue without live search, LLM ranking, citation counts, or later strategy performance.

Canonical input:

- reuse key: `arxiv/q-fin/2021/metadata`
- artifact: `docs/research/data/arxiv_qfin_2021.json`
- canonical record count: 1,132
- canonical snapshot SHA-256: `a1ebbbd25ae65b5bce391ccb8ded1a27fa7c013102581251cc1f6ee4e73a948c`

The selector resolves this input through `scripts/snapshot_store.py` and verifies the artifact SHA before reading it.

## Relationship to the reproduction registry

The repository also contains the curated reproduction registry at `docs/research/catalogs/2021_arxiv_finance_registry.json` and its storage/state-machine contract in `docs/specs/paper_reproduction_store.md`.

These artifacts have different roles:

```text
1,132-paper frozen discovery universe
  -> deterministic metadata selection manifest
  -> paper/version inspection
  -> explicit curation into 2021_arxiv_finance_registry.json
  -> source/data discovery and materialization
  -> method implementation
  -> empirical reproduction
  -> PIT/OOS/cost validation
  -> #claims eligibility
```

A `SELECT` result never appends a paper to the reproduction registry automatically. Registry curation is a separate evidence-bearing transition. Likewise, a paper already present in the reproduction registry does not receive a higher Stage A score merely because it was curated there.

## Time semantics

This is **ex-post research triage**, not a reconstruction of a 2021 paper-ranking decision.

The canonical arXiv snapshot was retrieved on `2026-08-13T09:02:34Z`. arXiv metadata can reflect versions and metadata revisions made after the initial 2021 submission. Therefore `title`, `abstract`, and version-related metadata must not be treated as a point-in-time 2021 information set.

A later paper-level PIT stage must pin the paper version and the timestamp at which that version became public before claiming that a strategy could have been specified at that time.

Current citation counts, later journal outcomes, and post-2021 strategy performance are forbidden selector inputs. `research_importance` remains `UNASSESSED` in Stage A.

## Decisions

- `SELECT`: prioritize for paper-level inspection only.
- `REVIEW`: potentially relevant, but metadata evidence is insufficient for automatic inspection priority.
- `REJECT`: do not prioritize from metadata. Missing required metadata fails closed.

`SELECT` is **not** approval for reproduction, registry inclusion, PIT integrity, OOS performance, transaction-cost viability, or publication to `#claims`.

## Deterministic inputs

The selector consumes only:

1. the accepted snapshot resolved by reuse key;
2. `docs/research/catalogs/arxiv_qfin_selector_rules_v1.json`;
3. the deterministic selector implementation.

The rules file fixes required fields, phrase lists, thresholds, weights, forbidden decision inputs, selector version, and tie-breaking. Matching is case-folded and phrase-boundary aware; for example, the term `data` does not match the substring in `metadata`.

No network request, citation API, LLM call, randomness, current clock, generated timestamp, or current reproduction-registry membership participates in the selection.

## Output contract

The canonical manifest is:

`docs/research/catalogs/arxiv_qfin_2021_selection_manifest.json`

Every candidate records:

- arXiv identity and category metadata;
- `research_importance`;
- investment-relevance metadata cues;
- method, data, PIT, OOS, and transaction-cost metadata cues;
- look-ahead warning;
- implementation-cost status;
- `SELECT | REVIEW | REJECT`;
- deterministic priority score;
- reason codes and matched-term evidence;
- selector version;
- source snapshot SHA-256.

The manifest also records the rules SHA-256, snapshot identity, summary counts by decision/category, selection semantics, and the look-ahead contract. It intentionally has no run timestamp so identical canonical input plus identical rules produces byte-stable output.

## Promotion boundary

The repository's existing validation and reproduction policies remain authoritative. No Stage A metadata result can skip paper/version inspection, explicit registry curation, PIT input freezing, empirical reproduction, chronological OOS, or implementation-cost gates.

## Reproduction

```bash
python scripts/select_arxiv_qfin_papers.py \
  --reuse-key arxiv/q-fin/2021/metadata \
  --rules docs/research/catalogs/arxiv_qfin_selector_rules_v1.json \
  --output docs/research/catalogs/arxiv_qfin_2021_selection_manifest.json

python tests/test_arxiv_qfin_selection.py
python scripts/snapshot_store.py audit
```
