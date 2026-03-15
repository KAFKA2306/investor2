---
name: mixseek-data-pipeline
description: |
  Use when preparing market data for backtesting—splitting into train/eval, handling missing values, and validating data quality.
  Input: date range, universe, data source. Output: clean datasets ready for backtesting.
  Ensures data integrity and separates training signals from evaluation periods.
---

# Mixseek Data Pipeline

## Overview

Prepares and validates market data for backtesting. Handles data splitting, missing value imputation, and quality assurance. Ensures train/eval separation to prevent data leakage.

**When to use:**
- Before backtesting multiple signal formulas
- Data quality validation required
- Train/eval split needed (prevent overfitting)
- Custom data sources integrated
- Historical price + volume data alignment

## Input Specification

```json
{
  "data_config": {
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "universe": "jp_stocks_300",
    "data_sources": [
      {
        "name": "j_quants",
        "fields": ["open", "high", "low", "close", "volume"]
      }
    ]
  },
  "split_config": {
    "train_end_date": "YYYY-MM-DD",
    "eval_start_date": "YYYY-MM-DD"
  }
}
```

## Data Pipeline

### Step 1: Data Loading
- Fetch OHLCV data from specified sources (J-Quants, Yahoo Finance, etc.)
- Load for all securities in universe
- Validate timestamps align across sources

### Step 2: Data Cleaning
- **Remove duplicates**: Keep first occurrence by timestamp
- **Forward fill**: Missing values within 5-day gap
- **Exclude**: Securities with >10% missing data
- **Drop**: Rows with NaN after cleaning

### Step 3: Calculate Derived Fields
- **Returns**: `(close[t+1] - close[t]) / close[t]`
- **Log returns**: `ln(close[t+1] / close[t])`
- **Volatility**: 5-day rolling std of returns
- **Volume ratio**: `volume[t] / mean(volume, 20)`

### Step 4: Train/Eval Split
```
Full Dataset [start_date ---- train_end_date | eval_start_date ---- end_date]
                           ↓
                        Train Set (for signal design)
                                           ↓
                                        Eval Set (for unbiased backtest)
```

- **Train period**: Used for hyperparameter tuning, understanding signal behavior
- **Eval period**: Held-out, never seen during signal design
- **Gap (optional)**: 5-day buffer between train/eval to avoid leakage

### Step 5: Quality Checks

| Check | Threshold | Action |
|-------|-----------|--------|
| **Missing data** | <8% of observations | Pass |
| **Price continuity** | Daily returns within [-0.3, 0.3] | Pass (flag extreme) |
| **Volume consistency** | Coefficient of variation < 2.0 | Pass |
| **Coverage** | >95% securities in universe present | Pass |

### Step 6: Output Structure

```json
{
  "train_dataset": {
    "period": "YYYY-MM-DD to YYYY-MM-DD",
    "shape": [502, 300, 5],
    "fields": ["open", "high", "low", "close", "volume"],
    "data_path": "path/to/train_data.parquet"
  },
  "eval_dataset": {
    "period": "YYYY-MM-DD to YYYY-MM-DD",
    "shape": [251, 300, 5],
    "fields": ["open", "high", "low", "close", "volume"],
    "data_path": "path/to/eval_data.parquet"
  },
  "quality_report": {
    "missing_rate": 0.032,
    "coverage": 0.985,
    "price_continuity": "pass",
    "volume_consistency": "pass"
  },
  "metadata": {
    "universe": "jp_stocks_300",
    "data_sources": ["j_quants"],
    "generated_at": "YYYY-MM-DDTHH:MM:SSZ"
  }
}
```

## Data Handling Patterns

### Missing Data Strategy
```
Gap < 1 day:   Forward fill (price unchanged)
Gap 1-5 days:  Linear interpolation of returns
Gap > 5 days:  Exclude security for that period
```

### Outlier Handling
```
Daily return > ±30%:  Flag as extreme, keep in data
Volume spike > 5x:    Keep (may be signal)
Price gap > 10%:      Investigate, keep if justified
```

## Implementation Notes

- **Deterministic**: Same input → same output
- **Non-invasive**: Minimal data transformation
- **Transparent**: Quality report shows all filters applied
- **Scalable**: Handles 300+ securities, 2+ years of data

## Edge Cases

- **Insufficient data**: Return error if <100 trading days in eval
- **All missing universe**: Return error with diagnostics
- **Single security**: Still process (edge case but valid)
- **Future date**: Return error (backtest only on historical)

## Integration with Pipeline

```
[Raw market data: J-Quants, Yahoo, etc.]
    ↓
[mixseek-data-pipeline] ← YOU ARE HERE
    ↓ (train + eval datasets)
[Backtest Engine] (executes formulas)
    ↓
[Ranking & Scoring] (compares results)
    ↓
[Competitive Framework output]
```

This skill is foundational—clean data ensures all downstream metrics are reliable.
