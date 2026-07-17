# Time-tested alpha selection policy

## Decision

AAARTS prioritizes hypotheses that have survived independent time and implementation tests over hypotheses selected mainly because they are recent, complex, or novel.

The default research sequence is:

```text
Established hypothesis
  -> point-in-time reproduction
  -> chronological OOS test
  -> post-publication test
  -> cross-market or cross-regime test
  -> cost, liquidity, and capacity test
  -> constrained LLM augmentation
  -> final selection or rejection
```

## Evidence basis

Published predictors commonly weaken outside their original samples and after publication.

- McLean and Pontiff report that returns for 97 published predictors were 26% lower out of sample and 58% lower after publication. https://doi.org/10.1111/jofi.12365
- Hou, Xue, and Zhang report that 65% of 452 anomalies failed a conventional replication hurdle after mitigating microcaps with NYSE breakpoints and value-weighted returns; 82% failed under their multiple-testing hurdle. https://doi.org/10.1093/rfs/hhy131

These findings do not mean that old research is automatically valid. They mean that publication recency and the original in-sample result are weak selection criteria.

## Required candidate record

Every alpha candidate must record:

| Field | Required content |
|---|---|
| Source | Paper, practitioner source, or internal hypothesis |
| Publication date | Date the hypothesis became publicly available |
| Original sample | Market, universe, and start/end dates |
| Mechanism | Risk, behavioral, friction, information-delay, or accounting mechanism |
| Signal definition | Exact formula, lag, weighting, and rebalance rule |
| PIT status | Whether each input existed at the decision timestamp |
| Reproduction | Original-sample reproduction and deviations |
| Chronological OOS | Untouched period selected before evaluation |
| Post-publication | Result after public dissemination |
| External replication | Other market, regime, or dataset |
| Trading realism | Turnover, spread, slippage, borrow, liquidity, and capacity |
| Factor exposure | Dependence on known factors and industries |
| Robustness | Nearby parameters and alternate defensible definitions |
| LLM contribution | Extraction, normalization, implementation, filtering, or extension |
| Verdict | Accept, quarantine, or reject with reason |

## Hard gate

A candidate cannot be promoted without a machine-readable OOS artifact containing:

- frozen input identifiers or hashes;
- the exact split dates;
- the locked signal definition;
- sample counts;
- return, risk, drawdown, and statistical results;
- cost assumptions;
- the rejection criterion; and
- a reproducible command or test.

Narrative claims, classification accuracy, novelty scores, and an in-sample backtest do not satisfy this gate.

## LLM boundary

LLMs may reduce the cost of applying an existing hypothesis to modern data. They may extract disclosures, normalize terminology, generate reproducible code, and test narrative-to-financial consistency.

LLMs must not turn an unsupported narrative into accepted alpha. Every LLM-derived extension must be evaluated against the unaugmented baseline on the same untouched OOS split.

## Scoring

Research priority may use:

```text
survival_score =
    chronological_oos
  + post_publication_survival
  + cross_market_replication
  + point_in_time_integrity
  + after_cost_viability
  + capacity
  + factor_orthogonality
  + parameter_stability
  + mechanism_clarity
  + implementation_simplicity
```

Novelty is metadata only. It receives no positive score.

## Empirical reference implementation

The repository includes a frozen post-publication momentum test:

- Report: `docs/research/post_publication_momentum_oos.md`
- Result: `docs/research/post_publication_momentum_oos.json`
- Script: `scripts/verify_post_publication_momentum.py`
- Test: `tests/test_post_publication_momentum.py`

The result is deliberately negative in the later holdout. That is evidence that the falsification gate is operating as intended.
