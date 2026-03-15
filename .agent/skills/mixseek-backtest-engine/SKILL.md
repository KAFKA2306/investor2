---
name: mixseek-backtest-engine
description: |
  Use when executing backtests on Qlib signal formulas to compute Sharpe ratio, IC, and max drawdown.
  Input: Qlib formula string, date range, universe. Output: performance metrics (Sharpe, IC, MaxDD).
  Integrates with mixseek-competitive-framework to evaluate individual signal candidates.
---

# Mixseek Backtest Engine for TypeScript

## Overview

Executes independent backtests on Qlib signal formulas, computing standardized performance metrics (Sharpe ratio, information coefficient, max drawdown). Used by mixseek-competitive-framework to rank candidates.

**When to use:**
- Single Qlib formula needs evaluation
- Performance metrics required (Sharpe, IC, MaxDD)
- Backtesting against historical market data
- Feeding results into competitive ranking system

## Input Specification

```json
{
  "factor_id": "string",
  "formula": "Qlib expression string",
  "backtest_config": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "universe": "jp_stocks_300",
    "rebalance_frequency": "daily"
  }
}
```

## Backtest Execution Pipeline

### Step 1: Formula Validation
- Confirm Qlib syntax correctness
- Check for undefined variables/functions
- Log any warnings

### Step 2: Data Loading
- Fetch OHLCV + returns data for universe over date range
- Align data with rebalance frequency
- Handle missing data (forward fill or exclusion)

### Step 3: Signal Generation
- Execute formula on each trading day
- Compute signal values for all securities
- Normalize signals (z-score or rank)

### Step 4: Performance Calculation
For each day `t`:
1. **Rank Correlation**: Spearman correlation between signal values (at t) and next-day returns (t+1)
2. Store correlation value

Aggregate over all days:
- **Sharpe ratio**: `mean(correlations) / std(correlations)`
- **Information Coefficient (IC)**: Mean of rank correlations
- **Max Drawdown**: Peak-to-trough decline in cumulative correlation series

### Step 5: Output Structure

```json
{
  "factor_id": "string",
  "formula": "Qlib expression",
  "performance": {
    "sharpe": 2.15,
    "ic": 0.0424,
    "max_drawdown": 0.128
  },
  "metadata": {
    "backtest_period": "2024-01-01 to 2025-12-31",
    "universe": "jp_stocks_300",
    "days_evaluated": 502,
    "valid_observations": 498
  }
}
```

## Implementation Notes

- **Deterministic**: Identical formula + data = identical results
- **Fast**: Single formula evaluation (seconds)
- **Transparent**: Metrics computed from standardized definitions (Spearman rank correlation, Sharpe from daily correlations)
- **Scalable**: Parallel execution for multiple formulas

## Edge Cases

- **Insufficient data**: Return error if fewer than 20 valid days
- **Constant signal**: IC = 0, Sharpe = NaN (log warning)
- **Missing returns**: Exclude day from correlation calculation, continue
- **Extreme leverage**: Cap correlations at [-1, 1]

## Integration with Pipeline

```
[Competitive Framework generates formula candidates]
    ↓ (for each candidate formula)
[mixseek-backtest-engine] ← YOU ARE HERE
    ↓ (performance metrics)
[mixseek-ranking-scoring] (rank candidates)
    ↓
[CqoAgent] (deep audit)
```

This engine is independent—evaluate one formula at a time, output metrics.
