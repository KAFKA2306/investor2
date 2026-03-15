---
name: polymarket-alpha-miner
description: Analyzes top Polymarket traders to extract and categorize their alpha strategies (Information Arbitrage, Jim Simons Style, Whale Tracking, Carry Trade, AI Automation). Use when analyzing leaderboard leaders or reverse-engineering on-chain signals.
---

# Polymarket Alpha Miner

This skill provides a structured protocol for reverse-engineering the strategies of elite Polymarket traders to extract live alpha.

## 🚀 Alpha Mining Workflow

1. **Leaderboard Mining**: Identify high-profit/high-volume targets from the monthly/weekly leaderboard.
2. **Strategy Archetype Identification**: Map the target trader to one of the 5 core archetypes using [strategy-archetypes.md](references/strategy-archetypes.md).
3. **Trader Profile Analysis**: Check existing intelligence in [trader-profiles.md](references/trader-profiles.md) for known execution patterns.
4. **Execution Parameter Extraction**: Identify specific bet sizes, market categories, and entry/exit timing (latency).
5. **Strategy Prototyping**: Guide the development of an automated agent or manual execution plan based on the mined alpha.

## 📖 Key References

- **[trader-profiles.md](references/trader-profiles.md)**: Current intelligence on Top 10 traders (majorexploiter, 0x2a2C..., etc.).
- **[strategy-archetypes.md](references/strategy-archetypes.md)**: Detailed breakdown of the 5 core alpha patterns and their technical requirements.

## 🛠️ Execution Protocol

- **Information Arbitrage**: Prioritize speed and news-wire integration.
- **Jim Simons Style**: Focus on high-frequency, low-margin, diversified positions.
- **Whale Tracking**: Monitor specific wallets for large-volume "intent" signals.
- **Carry Trade**: Target low-risk, high-probability "Nothing Happens" events.
- **AI Automation**: Leverage market-making and cross-market correlation bots.
