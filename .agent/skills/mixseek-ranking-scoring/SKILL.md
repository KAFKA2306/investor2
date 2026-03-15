---
name: mixseek-ranking-scoring
description: |
  Use when aggregating backtest results across multiple signal candidates and ranking them by performance metrics.
  Input: array of performance metrics (Sharpe, IC, MaxDD). Output: ranked candidates with scores, winner metadata.
  Determines final competitive ranking and winner selection.
---

# Mixseek Ranking & Scoring System

## Overview

Aggregates backtest results from multiple Qlib signal formulas and produces deterministic ranking based on performance metrics. Feeds ranking into competitive selection and CqoAgent audit.

**When to use:**
- Multiple candidates have been backtested
- Need to rank by Sharpe ratio (or composite metrics)
- Selecting winner for downstream evaluation
- Generating transparency report (all candidates ranked)

## Input Specification

```json
{
  "candidates": [
    {
      "factor_id": "string",
      "formula": "Qlib expression",
      "performance": {
        "sharpe": 2.15,
        "ic": 0.0424,
        "max_drawdown": 0.128
      }
    },
    // ... more candidates
  ],
  "ranking_config": {
    "primary_metric": "sharpe",
    "tie_breaker": "ic",
    "direction": "descending"
  }
}
```

## Ranking Pipeline

### Step 1: Validate Input
- Check all candidates have required metrics
- Confirm metric values are numeric and in valid range
- Log any anomalies (e.g., negative Sharpe from low signal stability)

### Step 2: Apply Primary Ranking
Sort candidates by `primary_metric` (Sharpe ratio):
- Higher Sharpe = better rank
- Store original position for transparency

### Step 3: Handle Ties
If two candidates have identical Sharpe:
1. Apply `tie_breaker` metric (IC by default)
2. If still tied: alphabetical by factor_id

### Step 4: Compute Deltas
For each candidate, compute distance from winner:
- `delta_sharpe = winner_sharpe - candidate_sharpe`
- Percentage drop from best performer

### Step 5: Output Structure

```json
{
  "winner": {
    "rank": 1,
    "factor_id": "string",
    "formula": "Qlib expression",
    "performance": {
      "sharpe": 2.15,
      "ic": 0.0424,
      "max_drawdown": 0.128
    }
  },
  "rankings": [
    {
      "rank": 1,
      "factor_id": "...",
      "sharpe": 2.15,
      "ic": 0.0424,
      "delta_from_winner": 0.0
    },
    {
      "rank": 2,
      "factor_id": "...",
      "sharpe": 1.87,
      "ic": 0.0391,
      "delta_from_winner": -0.28
    },
    // ... remaining candidates
  ],
  "scoring_metadata": {
    "total_candidates": 3,
    "ranking_metric": "sharpe_ratio",
    "tie_breaker": "ic",
    "evaluation_date": "YYYY-MM-DD"
  }
}
```

## Scoring Rules

| Metric | Range | Interpretation |
|--------|-------|-----------------|
| **Sharpe** | (-∞, +∞) | Daily correlation volatility-adjusted mean. >1.8 is strong; >2.0 is excellent |
| **IC** | [-1, 1] | Information coefficient (rank correlation). >0.04 is meaningful |
| **Max DD** | [0, 1] | Peak-to-trough drawdown. <0.15 is acceptable |

## Implementation Notes

- **Transparent**: All candidates ranked, deltas computed
- **Deterministic**: Same input always produces same ranking
- **Tie-breaking**: Predictable (metric then alphabetical)
- **Delta computation**: Shows gap to best performer

## Edge Cases

- **Single candidate**: Ranks as winner with empty `rankings` array
- **All candidates tied**: Use alphabetical factor_id ordering
- **Negative Sharpe**: Valid (indicates poor signal stability), still rankable
- **Zero candidates**: Return error with diagnostics

## Integration with Pipeline

```
[Backtest Engine produces metrics for each formula]
    ↓ (batch of results)
[mixseek-ranking-scoring] ← YOU ARE HERE
    ↓ (winner + rankings)
[Competitive Framework output] (integrates with CqoAgent)
    ↓
[Quality Gate] (Sharpe > 1.8, IC > 0.04)
```

This skill is purely deterministic—sort, compute deltas, output.
