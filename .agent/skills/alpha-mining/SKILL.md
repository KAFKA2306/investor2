---
name: alpha-mining
description: MANDATORY TRIGGER: Invoke for alpha factor discovery, formula generation, and backtesting within Qlib. Use when mining novel alpha factors, validating factor authenticity via AAARTS quality gates, optimizing factor performance, or preparing alpha candidates for production deployment. Essential for Ralph Loop workflows.
origin: local-git-analysis
---

# Alpha Mining & Qlib Optimization Skill

Expertise in generating, validating, and optimizing alpha formulas in Qlib format.

## When to Use
Use for alpha mining related tasks in this project.

## Core Concepts
- **Qlib Operator**: basic operators such as `$close`, `$open`, `Ref($close, 1)`, `Mean($close, 5)`, `Std($close, 10)`, etc.
- **Alpha Expression Syntax Requirements**: avoid invalid operations (e.g., division by zero); proper placement of normalization (Rank, CS_ZScore).
- **Performance Metrics**: interpretation of IC (Information Coefficient), IR (Information Ratio), drawdown, and Sharpe Ratio.

## AAARTS (Alpha Authenticity & Reality-Truth System)
A three-stage validation pipeline to ensure the reliability of alpha factors.

### Phase 1: Description-AST Consistency
- **Logic**: Validate consistency between the natural language description and the implemented code (AST).
- **Action**: If variables and functions mentioned in the description do not match those used in the AST, reject immediately.
- **Principle**: Prevent the introduction of alpha factors whose description and content diverge.

### Phase 2: Calculation Execution & NaN Propagation
- **Logic**: Do not fill missing data (e.g., undefined `macro_cpi`) with zeros; treat as NaN.
- **Action**: If NaN appears in the calculation, the final performance metric will be NaN and will be excluded in Phase 3.
- **Principle**: Do not tolerate false alphas caused by incomplete data; prioritize computation integrity.

### Phase 3: Strict Backtest Validation
- **Logic**: Final assessment using fixed or regime-adaptive thresholds.
- **Thresholds**: (See the Quality Gate section for details)
- **Error Behavior**: If a metric is NaN, or if any threshold is not met, reject immediately.

## Quality Gate Review Criteria
The generated alpha formula is evaluated using a weighted average of four metrics (all normalized to [0, 1]) to yield a Fitness Score.

### 1. Correlation Score
- **Logic**: The average of the absolute Pearson correlation between factor values and returns.
- **Normalization**: avg_corr / 0.3 (cap at 1.0). A correlation of 0.3 or higher earns full marks.

### 2. Constraint Score
- **Thresholds**: 
    - Sharpe Ratio >= 1.5
    - Information Coefficient (IC) >= 0.04
    - Max Drawdown <= 0.10
- **Normalization**: number of constraints satisfied / total number of constraints.

### 3. Orthogonality Score (Novelty)
- **Logic**: Jaccard distance with the existing Playbook (ts-agent/data/playbook.json).
- **Formula**: Jaccard = 1 - (intersection / union) (calculated on the set of operators and columns).
- **Goal**: Avoid overlap with existing methods and explore unseen alpha spaces.

### 4. Backtest Score
- **Normalization**: 
    - Sharpe scaled from [1.5, 2.0] to [0, 1]
    - IC scaled from [0.04, 0.08] to [0, 1]
- **Final**: Average of both.

## Regime-Adaptive Verification
Market environment adaptation to different regimes (RISK_ON / NEUTRAL / RISK_OFF) with dynamic thresholds.

### 1. Multiplier-Based Adaptation
Apply regime-specific multipliers to the baseline thresholds to compute execution thresholds.
- **RISK_ON**: Sharpe × 1.1, IC × 1.0 (stricter in bullish markets)
- **NEUTRAL**: Sharpe × 0.9, IC × 0.8
- **RISK_OFF**: Sharpe × 0.35, IC × 0.25 (lenient in bearish markets to capture actionable signals)

### 2. Fixed Risk Limits
Regardless of regime, the MaxDrawdown 0.1 (10%) constraint is always fixed. Risk management should be an absolute standard independent of market sentiment.

## Alpha Formula (DSL) Specifications and Limitations
- **Allowed Operators**: `rank(), scale(), abs(), sign(), log(), max(), min(), Mean(), Std(), Ref()`
- **Allowed Columns**: `$close $open $high $low $volume $vwap $macro_iip $macro_cpi $macro_leverage_trend $segment_sentiment $ai_exposure $kg_centrality`
- **Validation**:
    - Must be a single line starting with `alpha = `
    - Undefined columns or operators cause immediate rejection (auto-repair is attempted but no fallback if it fails)

## Council of Quants Review Criteria
- **Risk Manager Review**: Is the maximum drawdown within acceptable bounds? Does the Sharpe Ratio meet the minimum standard?
- **Alpha Hunter Review**: Does the P-Value satisfy the significance level (typically below 0.05)?
- **Regime Specialist Review**: Do the current market regime (Bull/Bear/Uncertain) and the alpha logic align?

## Code Examples
1. **Formula Generation**: Proposing new alpha formulas with an LLM.
2. **Validation**: Syntax check via `dsl_validator.ts` and past-data verification via `backtest_scorer.ts`.
3. **Strategic Reasoning**: Multidimensional quality evaluation via the Quality Gate and Council of Quants.
4. **Refinement**: Improving underperforming formulas by combining with orthogonal operators.

## Ralph Loop Domain Pivot
If exploration repeatedly fails, autonomously switch to a new market domain (sector, time frame, factor type).
- **Trigger**: Consecutive failures count (`consecutiveFailures`) reaches 2 or more.
- **Action**:
  1. Record the recently failed domain as a Forbidden Zone with a TTL.
  2. Evaluate the current market regime (Volatility/Momentum).
  3. Select the farthest domain from the Forbidden Zone (Euclidean/Cosine distance).
  4. Temporarily relax the Fitness Threshold (e.g., 0.5 → 0.4 for 3 cycles) to bootstrap exploration.
- **Logging**: Record the pivot reason in REASON_DESC.md based on Novelty/Orthogonality, Metric Thresholds, and Hypothesis Validity.

## Best Practices
- Alphas should always be normalized cross-sectionally using Rank(Formula) or CS_ZScore(Formula).
- Strictly check for future references such as Ref($close, -1).
- Generated formulas are typed in alpha_quality_optimizer_schema.ts to ensure consistency.