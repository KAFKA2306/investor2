# Prediction Market Trading Bot — Design Document

**Date**: 2026-03-10
**Status**: Design Approved ✅
**Scope**: Backtest/Simulation Only (No Live Trading)

---

## 1. Executive Summary

A **6-agent Team Agent system** for automated Polymarket market scanning, research, prediction, risk validation, and signal generation. Full pipeline runs within a single Claude Skill with rolling 90-day backtest windows to validate edge detection, position sizing, and learning loops.

**Key Characteristics**:
- **Input**: 300+ Polymarket market IDs, historical price data via API
- **Output**: JSON signals with Kelly-sized bets, edge > 4%, VaR-approved only
- **Validation**: Rolling backtest (Period 1: Day 0-90, Period 2: Day 30-120, Period 3: Day 60-150)
- **Learning**: Failure patterns → SQLite knowledge base → next cycle improvements

---

## 2. Architecture

### 2.1 Overall Design

```
┌──────────────────────────────────────────────┐
│ SKILL: polymarket-trading-bot                │
│ (Claude Agent SDK + Team Agents)             │
└────────────────┬─────────────────────────────┘
                 │
        ┌────────▼────────┐
        │ SwarmOrchestrator│
        │ (Parent Agent)   │
        └────────┬────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼──┐    ┌────▼────┐  ┌───▼────┐
│Scan  │    │Research │  │Predict │ ×2
└──────┘    └─────────┘  └────────┘
    │            │            │
    └────────────┼────────────┘
                 │
           ┌─────▼──────┐
           │ Risk Agent │ ×2 (parallel validation)
           └─────┬──────┘
                 │
           ┌─────▼──────┐
           │   Execute  │ (signal generation)
           └─────┬──────┘
                 │
           ┌─────▼──────┐
           │  Compound  │ (learning loop)
           └────────────┘
```

### 2.2 Data Flow

1. **Input** → Coordinator receives market IDs, time window (90d rolling)
2. **Scan** → Filter 300+ markets by liquidity, spread, time-to-close
3. **Research** (parallel) → Twitter/Reddit sentiment via NLP
4. **Predict** ×2 (parallel) →
   - Agent 1: XGBoost probability (historical tick data)
   - Agent 2: LLM probability (narrative + base rate)
5. **Risk** ×2 (parallel) →
   - Agent 1: Kelly Criterion + VaR 95%
   - Agent 2: Max Drawdown + Sharpe simulation
6. **Execute** → Merge results, check edge > 4%, output signals
7. **Compound** → Extract failure patterns, update knowledge base
8. **Output** → JSON signals with metrics, next scan priorities

---

## 3. Agent Responsibilities

| Agent | Input | Logic | Output |
|-------|-------|-------|--------|
| **ScanAgent** | Markets, prices, spreads | Filter: volume > threshold && spread < 5% && time_to_close > 24h | `{market_id, liquidity_score, spread, time_remaining}` |
| **ResearchAgent** | Market description, sentiment APIs | Twitter/Reddit scrape → NLP classification → Bayes update | `{market_id, sentiment_score, narrative}` |
| **PredictAgent** ×2 | Market data, research results | Agent 1: XGBoost (trained on historical ticks); Agent 2: LLM (narrative reasoning) | `{market_id, p_model_xgb, p_model_llm, confidence}` |
| **RiskAgent** ×2 | p_model, p_mkt, bankroll, max_exposure | Agent 1: Kelly + VaR; Agent 2: Max DD + Sharpe | `{market_id, f_kelly, bet_size, var_loss, approved}` |
| **ExecuteAgent** | All above | edge = p_model - p_mkt; IF edge > 0.04 && approved THEN signal | `{signals: [{market_id, bet_size, direction, reasoning}]}` |
| **CompoundAgent** | Historical trades, failures | Pattern extraction → knowledge base update → priority weights | `{lessons, next_scan_priority}` |

---

## 4. Core Formulas

### 4.1 Edge Detection

```
EV = p_model * b - (1 - p_model)
  where b = decimal_odds - 1

edge = p_model - p_mkt
TRADE_CONDITION: edge > 0.04  (≥4% mispricing required)
```

### 4.2 Position Sizing

```
Kelly Criterion (Full):
  f* = (p * b - (1 - p)) / b

Fractional Kelly (Safe):
  f = alpha * f*  (alpha = 0.25 to 0.5)

Bet Size:
  bet = f * bankroll
  (In backtest: fixed 1000 USDC per bet, f controls fraction)
```

### 4.3 Risk Constraints (ALL must pass)

```
1. Value at Risk (95% confidence):
   VaR = mu - 1.645 * sigma
   BLOCK IF: VaR > daily_limit (e.g., 500 USDC)

2. Maximum Drawdown:
   MDD = (Peak - Trough) / Peak
   STOP_NEW_TRADES IF: MDD > 8%

3. Total Exposure:
   total_exposure + bet <= max_exposure (e.g., 5000 USDC)
   REJECT IF: violates constraint

4. Model Consensus:
   correlation(p_xgb, p_llm) > 0.70
   REDUCE BET BY 50% IF: < 0.70
```

### 4.4 Model Accuracy

```
Brier Score (lower is better):
  BS = (1/n) * sum(p_i - o_i)^2
  Target: BS < 0.15 (excellent)
```

---

## 5. Signal Output Format

```json
{
  "timestamp": "2026-03-10T14:30:00Z",
  "backtest_window": "90d_rolling_period_2",
  "signals": [
    {
      "market_id": "0x123abc...",
      "market_title": "Will X happen?",
      "direction": "YES|NO",
      "bet_size_usdc": 150.50,
      "p_model_xgb": 0.68,
      "p_model_llm": 0.65,
      "p_model_consensus": 0.665,
      "p_market": 0.55,
      "edge": 0.115,
      "kelly_fraction": 0.25,
      "var_95_loss": 45.20,
      "liquidity_score": 0.92,
      "sentiment_score": 0.78,
      "narrative": "Strong bullish sentiment on Twitter",
      "confidence_level": "HIGH|MEDIUM|LOW",
      "risk_approved": true,
      "reasoning": "4% edge + 0.70 consensus + VaR within limit"
    }
  ],
  "aggregate_metrics": {
    "total_exposure": 1250.50,
    "max_drawdown_today": 0.032,
    "sharpe_ratio_ytd": 2.14,
    "win_rate": 0.684,
    "signals_generated": 5,
    "signals_approved": 4
  },
  "learning_updates": {
    "failed_trades_analyzed": 3,
    "new_lessons": [
      "Avoid markets with < 2 days to resolution",
      "Sentiment score < 0.3 has 80% loss rate"
    ]
  }
}
```

---

## 6. Compound Agent — Learning Loop

### 6.1 Failure Analysis

```
Failed Trade
  ↓
Root Cause Analysis:
  - edge < expected?
  - market liquidity collapsed?
  - sentiment score overfit?
  - p_model prediction drift?
  ↓
Pattern Extraction:
  - same pattern 3+ times?
  - specific market category?
  - time-of-day effect?
  ↓
Knowledge Base Update:
  SQLite: lessons_learned table
  - lesson TEXT
  - pattern_type TEXT
  - confidence_score FLOAT
  - frequency INT
  - priority_weight FLOAT (for next Scan)
```

### 6.2 Learning DB Schema

```sql
CREATE TABLE lessons_learned (
  id INTEGER PRIMARY KEY,
  lesson TEXT,
  pattern_type TEXT,
  confidence_score FLOAT,
  frequency INT,
  impact_on_returns FLOAT,
  created_at TIMESTAMP,
  priority_weight FLOAT
);

Examples:
- "sentiment_score < 0.3 → 80% loss rate"
- "resolution_time < 2 days → high volatility"
- "spread > 0.10 → slippage risk"
```

---

## 7. Rolling Backtest Strategy

```
Period 1: [Day 0-90]
  ├─ Execute backtest
  ├─ Compute metrics: Sharpe, Win Rate, Max DD
  └─ Learn: Extract 5-10 lessons

Period 2: [Day 30-120]
  ├─ Apply learning from Period 1
  ├─ Execute backtest
  ├─ Check: Metrics improved?
  └─ Learn: Extract new patterns

Period 3: [Day 60-150]
  ├─ Apply learning from Periods 1-2
  ├─ Execute backtest
  ├─ Final validation: Stable metrics?
  └─ Report: Overall Sharpe, Win Rate, stability
```

---

## 8. Quality Gates

### 8.1 GO Decision (Signal Approved)

```
✓ Sharpe Ratio ≥ 1.8
✓ Information Coefficient (IC) ≥ 0.04
✓ Max Drawdown ≤ 10%
✓ Win Rate ≥ 55%
✓ Model Consensus ≥ 0.70
```

### 8.2 HOLD Decision

```
One or more metrics below threshold
→ More learning cycles needed
→ Extend backtest window
```

### 8.3 PIVOT Decision

```
3 consecutive failed cycles
→ Scan/Predict/Risk component failure
→ Domain change (new market category)
→ Re-architecture required
```

---

## 9. Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Orchestrator | TypeScript + Claude Agent SDK | investor project alignment |
| ScanAgent | TypeScript + Zod | Polymarket API + type safety |
| ResearchAgent | Python + NLTK/spaCy | NLP sentiment analysis |
| PredictAgent | XGBoost (Python) + LLM (TypeScript) | Hybrid ensemble |
| RiskAgent | TypeScript + Decimal.js | Precision money math |
| ExecuteAgent | TypeScript | Signal generation |
| CompoundAgent | Python + SQLite | Knowledge base management |
| Testing | Jest (TS) + pytest (Py) | Unit + integration tests |
| Skill Definition | YAML + Markdown | SKILL.md format |

---

## 10. Validation Strategy

### 10.1 Unit Tests

- ScanAgent: market filtering logic (mock markets)
- PredictAgent: probability outputs (synthetic data)
- RiskAgent: Kelly/VaR calculations (boundary cases)
- CompoundAgent: pattern extraction (failure scenarios)

### 10.2 Integration Tests (Rolling Windows)

```
Period 1: Backtest → Validate Sharpe, Win Rate
Period 2: Backtest + Learning → Validate improvement
Period 3: Backtest + Learning → Validate stability
```

### 10.3 Audit Trail

- All trades logged to `logs/polymarket/trades_*.json`
- All signals logged to `logs/polymarket/signals_*.json`
- All learning updates to SQLite `lessons_learned`

---

## 11. Out of Scope

- **Live Trading**: Backtest/simulation only
- **Real Money Execution**: No on-chain transactions
- **API Key Management**: Assumed secure environment
- **Market Microstructure**: Ignores slippage, latency
- **Regulatory Compliance**: For educational/research purposes

---

## 12. Success Criteria

| Metric | Target | Window |
|--------|--------|--------|
| Sharpe Ratio | ≥ 2.0 | 90 days |
| Win Rate | ≥ 68% | 90 days |
| Max Drawdown | ≤ 5% | 90 days |
| Brier Score | ≤ 0.15 | per agent |
| Consensus (XGBoost vs LLM) | ≥ 0.70 | rolling |

---

## Appendix: References

- Polymarket API: `/prices-history`, `/markets`, `/orderbook`
- Claude Agent SDK: Subagents, Task tool, parallel execution
- XGBoost: `predict_proba()` for probability output
- Kelly Criterion: Fractional sizing with alpha = 0.25-0.5
- VaR 95%: Normal distribution assumption

---

**Approved by**: User
**Design Date**: 2026-03-10
**Next Step**: Implementation Planning (writing-plans skill)
