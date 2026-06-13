---
name: market-intelligence
description: Detect whale movements, latent economic signals, and event-driven opportunities across on-chain and macro data. Use when monitoring large investor position changes (13F filings), hunting alpha from macro regime shifts, detecting anomalies in market structure (flows, correlations, volatility regimes), tracking earnings calendar catalysts, or identifying short-squeeze candidates.
origin: local-git-analysis
---

# Market Intelligence & Signal Detection Skill

Expertise in detecting on-chain data (whale movements), news events, and latent economic signals to identify investment opportunities.

## When to Use
Use this skill for market intelligence-related tasks in this project.

## Core Concepts
- **Whale Watching**: Movement of large investors' wallets, fund flows between centralized exchanges (CEX) and decentralized exchanges (DEX), and issuance/redemptions of stablecoins.
- **Latent Signals**: Underlying economic trends hidden behind surface-level news, changes in correlations between sectors.
- **Event Analysis**: Evaluating the short- and medium-term market impacts of events such as earnings announcements, employment statistics, and central bank policy decisions.

## Code Examples
1. **Trend Monitoring**: Continuous monitoring of key on-chain/off-chain data sources.
2. **Contextualization**: Interpreting detected events in light of the current macro environment and past similar cases.
3.3. **Signal Ranking**: Prioritizing signals based on confidence, expected return, and time horizon.

## Best Practices
- Signals should not rely on a single source; always corroborate with multiple independent sources (both on-chain and off-chain).
- Apply filtering criteria rigorously to eliminate false signals (e.g., wash trades).

## Implementation Reference

### Available Data Sources
- **J-Quants**: Japanese stock data, real-time prices, and market indicators
- **EDINET**: Japanese-listed company financial statements and audit reports (fetched with `task edinet:fetch`)
- **FRED Economic Data**: US macroeconomic indicators (interest rates, unemployment, etc.)
- **Yahoo Finance**: Global equity and foreign exchange data

### Commands
```
task pipeline:verify          # Verify overall pipeline integrity
task stats:summarize          # Generate market statistics summary
task polymarket:fetch         # Retrieve Polymarket prediction market data
```

### Agent Integrations
- **whale-watcher-agent**: Detects changes in large investors' positions from 13F filings
- **macro-top-down-agent**: Macro-environment analysis and sector correlation detection
- **event-driven-analyst-agent**: Short-term event opportunities (short-squeeze candidates, M&A radar)

### Data Validation Skills
- Inconsistency detection: `polymarket-data-validation`
- Schema definitions: Refer to `src/schemas.ts`