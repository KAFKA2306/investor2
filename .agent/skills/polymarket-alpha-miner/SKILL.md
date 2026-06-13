---
name: polymarket-alpha-miner
description: Extract time-series alpha signals from Polymarket event calendars, implied probabilities, and order flow dynamics. Use when mining alpha from prediction market microstructure, detecting regime changes in event probabilities, backtesting alpha hypotheses on Polymarket data, or identifying mispriced outcomes relative to consensus forecasts.
origin: local-git-analysis
---

# Polymarket Alpha Miner Skill

Polymarket event calendars, implied probabilities, and order flow data provide specialized knowledge for extracting time-series signals unique to prediction markets.

## When to Use
Use for Polymarket alpha-miner-related tasks in this project.

## Core Concepts

- **Event Calendar Correlation**: Capture the realization times of earnings announcements, policy decisions, sports events, and shifts in market sentiment.
- **Implied Probability Extraction**: Derive market-implied probabilities from odds (e.g., YES = 0.65, NO = 0.35).
- **Liquidity Scoring**: Apply market depth and volume-based adjustments. Quantify the reduction in signal reliability under low liquidity conditions.
- **Order Flow Analysis**: From time-series patterns of large buys and sells (e.g., deviations from VWAP), estimate the time window of information advantage.

## Code Examples

1. **Event Calendar Scanning**: Search for upcoming events in the next N days and past market trends for the corresponding period.
2. **Implied Probability Decomposition**: Compute market-implied probabilities from odds and quantify deviations from historical realized frequencies (expectation).
3. **Order Flow Fingerprinting**: Analyze time-series of block trades (large orders) and price impact to detect signals indicative of insider information.
4. **Signal Strength Ranking**: Based on event progression, liquidity, and historical hit rate, output a signal confidence score.

## Best Practices

- Polymarket signals are specialized for short-term alpha (less than 1 week) and should function as a supplement to long-term fundamental analysis.
- Markets with extremely low liquidity (<$100k ADV) should be excluded from signal generation due to low statistical reliability.
- Order-flow analysis should always be conducted across multiple time frames (1 minute, 5 minutes, 1 hour) to distinguish the noise floor from true signals.