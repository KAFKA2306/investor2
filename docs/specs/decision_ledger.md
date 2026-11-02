# Decision Ledger contract

The canonical decision path is:

`DecisionSnapshot -> HumanDecisionRecord -> OutcomeEvaluationPlan -> DecisionReview -> projections`

`DecisionSnapshot` remains the immutable decision-time research state. `HumanDecisionRecord` records the human action (`buy | add | abstain`) against an exact 40-character snapshot commit and references the outcome plan fixed no later than the decision time. Reusing a decision ID with different contents is rejected.

`OutcomeEvaluationPlan` fixes the benchmark, transaction-cost assumption, primary outcome metric, downside metric, missing-outcome policy, overlap handling, aggregation weight, minimum evidence count, and verdict thresholds before outcome evidence is observed.

A ledger review must preserve the same decision ID, exact snapshot commit, and outcome-plan reference. Outcome evidence cannot predate the human decision or postdate the review. Derived `delta` is checked against `primary_outcome - benchmark_outcome - transaction_cost`.

Single-decision and aggregate views are generated projections, not additional ledgers. Unresolved outcomes remain in the denominator as unresolved. Synthetic records are excluded from investment-outcome aggregation. With zero actual decisions, or fewer resolved decisions than the plan requires, the valid terminal verdict is `INSUFFICIENT_EVIDENCE`.

The aggregate projection is explicitly an `investment_outcome` layer. Operational/system-health metrics must remain in a separate projection and are not accepted as evidence of investment value.

Focused verification:

```sh
bun test tests/decision_snapshot.test.ts tests/decision_ledger.test.ts
```

Repository gate:

```sh
task check
```
