---
name: polymarket
description: Execute prediction market trades on Polymarket CLOB with Kelly-criterion position sizing and event-driven strategies. Use when deploying prediction market trading algorithms, executing trades with optimal position sizing, managing exposure to event-driven alpha signals, or backtesting trading strategies on implied probability curves.
origin: local-git-analysis
---

# Polymarket Trading Bot Skill

Expert knowledge for efficiently trading prediction markets in coordination with Polymarket's CLOB (Central Limit Order Book).

## When to Use
Use when working with Polymarket-related tasks in this project.

## Core Concepts
- **CLOB API characteristics**: adherence to rate limits, generation of signed orders, gasless order management.
- **Betting strategies**: capital management based on the Kelly criterion, detection of odds distortions, event-driven position unwinding.
- **Data structures**: Validation of Polymarket-specific messaging using Zod schemas.

## Code Examples
1. **Market Discovery**: Extraction of ongoing events and high-liquidity markets.
2. **Backtesting**: Procedures for validating historical data using `backtest_core.ts`.
3. **Execution**: Opening positions, updating limit orders, and setting stop-losses.

## Best Practices
- Before opening a position, always validate data integrity with `polymarket_schemas.ts`.
- Telemetry logs should be recorded via `telemetry_logger.ts`, automating anomaly detection.