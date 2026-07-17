# Alpha Discovery Execution Runbook

> ⚠️ The commands in this document may refer to the main local pipeline repository. Confirm the active repository before execution.

This runbook defines the alpha-discovery process. The objective is not to maximize novelty or produce a favorable report. The objective is to reject weak hypotheses before they reach portfolio construction.

## Alpha discovery cycle

### 1. Select a defensible seed

Prefer a hypothesis with a clear mechanism and an auditable definition. A recent publication receives no automatic preference.

The candidate record must include its source, publication date, original sample, signal formula, data lag, weighting, rebalance rule, and expected implementation frictions.

### 2. Lock the protocol

Before reading OOS results, record:

- development and validation periods;
- untouched chronological OOS period;
- publication cutoff when applicable;
- universe and exclusions;
- PIT availability rule;
- transaction-cost assumptions;
- primary metric and rejection threshold; and
- allowed parameter variants.

The locked protocol must be stored with the run artifact.

### 3. Implement the baseline without an LLM extension

Translate the original or baseline hypothesis into the Alpha DSL or equivalent deterministic implementation.

An LLM may assist with code generation, but the resulting signal must be reproducible without model memory or conversational context.

### 4. Reproduce and falsify

Run, in order:

1. original-sample reproduction;
2. chronological OOS;
3. post-publication OOS;
4. cross-market or cross-regime replication;
5. cost, liquidity, borrow, and capacity sensitivity;
6. known-factor and industry-exposure analysis;
7. parameter-neighborhood stability.

Any failure is recorded. Failures must not be hidden by changing the split, metric, or parameter grid after results are observed.

### 5. Add the LLM contribution

Only after the deterministic baseline is measured may an LLM-based extraction or filter be added.

The augmented model must be compared with the baseline on the same untouched OOS period. The incremental result, not the combined model alone, determines whether the LLM adds value.

### 6. Emit the evidence artifact

Every run must emit a machine-readable artifact containing:

- input hashes or immutable source identifiers;
- split dates and observation counts;
- signal and portfolio definitions;
- gross and cost-adjusted metrics;
- drawdown and turnover;
- statistical uncertainty;
- failure reasons; and
- accept, quarantine, or reject verdict.

A human-readable summary may accompany the artifact but cannot replace it.

### 7. Capture knowledge

Update the playbook and memory with both successful signals and rejection rationales. Use logs to prevent repeated testing of the same failed hypothesis.

## Promotion gate

A candidate is rejected or quarantined when any material condition remains unresolved, including:

- look-ahead or survivorship leakage;
- no untouched chronological OOS result;
- post-publication collapse;
- dependence on microcaps or implausible liquidity;
- failure after reasonable cost assumptions;
- unstable nearby parameters;
- unexplained exposure to known factors; or
- a confidence interval compatible with no economically relevant edge.

Novelty is not a promotion criterion.

## Reference empirical test

Run the checked-in post-publication momentum verification:

```bash
python scripts/verify_post_publication_momentum.py \
  --input docs/research/data/ff_momentum_1994_2017.csv \
  --output docs/research/post_publication_momentum_oos.json

python -m pytest -q tests/test_post_publication_momentum.py
```

The report is at `docs/research/post_publication_momentum_oos.md`.

## Exception handling

- Missing or malformed data must fail loudly.
- If the OOS input is unavailable, the candidate remains unverified; an in-sample substitute is prohibited.
- If repeated variants are tested, the run must record the full trial count and apply an appropriate multiple-testing correction.
- If the research domain is saturated, stop generating variants and move to a different mechanism. Do not relabel minor parameter changes as novel hypotheses.
