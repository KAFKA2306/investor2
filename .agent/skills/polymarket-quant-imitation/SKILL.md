---
name: polymarket-quant-imitation
description: >
  MANDATORY TRIGGER: Invoke for any task involving Polymarket trading, 
  quant wallet research, on-chain transaction analysis, or leaderboard-based 
  imitation strategies. If the request mentions Polymarket, top traders, 
  leaderboard, Polygonscan, or transactional alpha extraction, this skill 
  must be used to follow the established reverse-engineering protocol.
---

# Polymarket Quant Imitation Skill

This skill defines the high-speed protocol for reverse-engineering top Polymarket quants to extract live alpha from on-chain movements.

## 🚀 When to Use
- When identifying top-performing wallets from the Polymarket leaderboard.
- When analyzing on-chain transaction history via Polygonscan.
- When reverse-engineering the entry/exit logic of professional traders.
- When configuring `QuantImitationAgent` or associated monitors.

## 📖 Usage Instructions

### 1. Leaderboard Mining
- Identify wallets with high Volume and consistent Profit across weekly/monthly timeframes.
- Extract the Polygon wallet addresses of these regular high-performance winners.

### 2. On-chain Forensics
- Use **[PolygonScanGateway](file:///home/kafka/finance/investor/ts-agent/src/io/market/polygon_scan_gateway.ts)** to fetch raw transaction data.
- Analyze "Transaction Timing" to determine the execution latency.
- Map "Signal Extraction" by correlating trade timestamps with external market events.

### 3. Execution & Imitation
- (Scripts are currently being rewritten to remove past biases and focus on real-time targets. Do NOT use old imitation scripts.)
- Use **[PolymarketArbAgent](file:///home/kafka/finance/investor/ts-agent/src/agents/polymarket_arb_agent.ts)** for execution with strict slippage/fee controls.

## 🛡️ Iron Rules

1.  NO ORACLE DEPENDENCY: We do not rely on lagging oracles. We trust the "intent" of top quants as the ultimate leading indicator.
2.  NO DUMMY KEYS: NEVER use placeholder private keys because fake credentials break execution flows and mislead operators.
3.  NO SAFETY NETS: We reject defensive `try-catch` blocks in core logic because silent failures are more dangerous than loud crashes in high-stakes trading.
4.  MINIMALISM: Keep data models focused on raw execution price and time, because over-engineered schemas introduce latency and review overhead.

## Best Practices
- Node Proximity: Always deploy the agent on a VPS geographically close to Polygon RPC nodes to minimize "Transaction Timing" lag.
- Edge Identification: Focus on markets where top quants exhibit clear information asymmetry (e.g., event outcomes, low-liquidity spikes).
- Configuration: Strictly use **[config/default.yaml](file:///home/kafka/finance/investor/config/default.yaml)** for all thresholds to ensure consistent operation across the fleet.
