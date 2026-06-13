---
name: trading-strategies
description: Mean reversion, statistical arbitrage, pairs trading, and portfolio hedging strategies with risk limits. Use when designing mean-reversion alpha factors, backtesting statistical arbitrage setups, constructing pairs trading hedges, building portfolio-level risk management rules, or evaluating hedging effectiveness across regimes.
origin: local-git-analysis
---

# Trading Strategies & Risk Management Skill

Expertise in Mean Reversion, Statistical Arbitrage, and Portfolio Hedging Strategies.

## When to Use
Use for tasks related to trading strategies within this project.

## Core Concepts
- **Mean Reversion**:
  - **Z-score**: A statistical measure of how far price deviates from its moving average. Typically entries are considered when |Z| > 2.
  - **Indicators**: RSI (Relative Strength Index), Bollinger Bands, moving-average deviation.
- **Statistical Arbitrage**:
  - **Pairs Trading**: A long/short strategy that exploits price divergence between two securities with high correlation within the same sector.
  - **Cointegration**: Emphasizes the stationarity of long-run price differentials rather than simple correlation.
- **Risk Hedging**:
  - **Tail Risk Hedging**: Downside protection using put options, inverse ETFs, and VIX-related instruments.
  - **Hedge Cost Management**: Strategy design to minimize the cost of protection (premiums, etc.).

## Code Examples
1. **Opportunity Scanning**: Screening for oversold/overbought securities using RSI or Z-score.
2. **Pairs Selection**: Identifying statistical arbitrage pairs based on historical correlation data.
3. **Hedge Design**: Selecting optimal hedging instruments based on the portfolio beta and sector concentration.
4. **Execution Triggers**: Establishing quantitative criteria for entry, take-profit, stop-loss, and hedge activation.

## Best Practices
- In mean-reversion strategies, rigorously distinguish price declines caused by fundamental breakdown (structural changes) from temporary deviations.
- Hedging should always function as insurance, avoiding deterioration of returns due to over-hedging.
- Even for highly correlated pairs, if event risk (M&A, earnings announcements, etc.) exists, they should be excluded from statistical arbitrage.