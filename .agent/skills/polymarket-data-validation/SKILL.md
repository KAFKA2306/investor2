---
name: polymarket-data-validation
description: Validate Polymarket event data integrity, detect anomalous odds (Z-score outliers, stale quotes), and ensure schema compliance before trading execution. Use when quality-gating market data before live trading, detecting data feed anomalies, validating event schemas against live Polymarket API responses, or auditing historical quote integrity for backtests.
origin: local-git-analysis
---

# Polymarket Data Validation Skill

Expertise to ensure the quality of Polymarket market data and to perform anomaly detection and integrity checks.

## When to Use
Use for polymarket data validation related tasks in this project.

## Core Concepts

- **Schema Validation**: Ensuring type safety for Polymarket events, odds, and market metadata using Zod.
- **Anomaly Detection**: Detect statistical outliers in odds (Z-score > 3σ), illiquidity (bid-ask spread widening), and book imbalance.
- **Integrity Checks**: Discrepancies between event times and the current time, concurrent quotes across multiple books, and deviations in the sum of probabilities (exceeding 100%).
- **Data Freshness**: Monitor cache update timestamps and rate-limit Windows.

## Code Examples

1. **Inbound Validation**: Immediately verify that event data received from the API satisfies the `PolymarketEventSchema`.

2. **Anomaly Detection**: Detect statistical outliers in odds movement rates, spreads, and volume profiles.

3.3. **Cross-Book Coherence**: Ensure odds from multiple market makers remain coherent; alert on significant divergence.

4. **Risk Flags**: Automatically identify trading risk factors such as illiquidity and abrupt movements near the event.

## Best Practices

- Validation errors should be propagated immediately (do not suppress). Anomalies should be detected early.
- Run multiple independent checks (schema, statistics, and cache freshness) in parallel; if any fail, REJECT.
- Record the output of the validation pipeline in `CanonicalLog` format to enable post hoc audits.

## Reference

### Schema Definition
**File**: `src/schemas.ts`
- `PolymarketEventSchema`: Unified schema for events, odds, and metadata
- `PolymarketMarketSchema`: Market-level integrity validation

### Execution
```
task polymarket:validate    # Validate all events and odds for consistency
```

### Error Recovery Strategies

| Anomaly Pattern | Response |
|---|---|
| Schema mismatch | REJECT - propagate as-is |
| Z-score > 3σ | ALERT - output anomaly detection log, proceed with caution in trading |
| Stale cache | REFRESH - re-query API and re-validate with the latest data |