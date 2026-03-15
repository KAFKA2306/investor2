# Polymarket Trading Bot Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a 6-agent Team Agent system that scans Polymarket, predicts market outcomes, validates risk, and generates trading signals via rolling 90-day backtests.

**Architecture:** SwarmOrchestrator (parent) coordinates 6 specialized subagents (Scan, Research, Predict ×2, Risk ×2, Execute, Compound) via Claude Agent SDK Task tool. Each agent runs independently with its own tool/model configuration. Results merge at Execute layer, failures analyzed by Compound layer with SQLite persistence.

**Tech Stack:** TypeScript (Coordinator, Scan, Risk, Execute) + Python (Research, Predict, Compound); Claude Agent SDK; Polymarket CLOB API; XGBoost; SQLite; Jest + pytest.

---

## Phase 1: Foundation & Project Setup

### Task 1: Create skill directory and SKILL.md

**Files:**
- Create: `.agent/skills/polymarket-trading-bot/SKILL.md`
- Create: `.agent/skills/polymarket-trading-bot/README.md`

**Step 1: Create SKILL.md with frontmatter**

Create `.agent/skills/polymarket-trading-bot/SKILL.md`:

```markdown
---
name: polymarket-trading-bot
description: |
  Autonomous prediction market trading bot using 6-agent swarm.
  Scans Polymarket, predicts outcomes with XGBoost+LLM, validates
  risk (Kelly/VaR), and generates backtest signals. Use when: running
  rolling 90-day backtests on 300+ markets with edge detection and
  learned failure patterns.
---

# Polymarket Trading Bot Skill

## Overview

[Full implementation details to be filled in after agent scaffold]

## Usage

\`\`\`bash
task run:polymarket-backtest --window 90d --markets 300
\`\`\`
```

**Step 2: Commit**

```bash
git add .agent/skills/polymarket-trading-bot/SKILL.md
git commit -m "feat: add polymarket-trading-bot skill directory structure"
```

---

### Task 2: Create TypeScript project structure for agents

**Files:**
- Create: `ts-agent/src/agents/polymarket/orchestrator.ts`
- Create: `ts-agent/src/agents/polymarket/scan_agent.ts`
- Create: `ts-agent/src/agents/polymarket/execute_agent.ts`
- Create: `ts-agent/src/agents/polymarket/types.ts`
- Create: `ts-agent/src/agents/polymarket/index.ts`
- Create: `ts-agent/src/io/polymarket/api_client.ts`
- Create: `ts-agent/src/schemas/polymarket_schemas.ts`

**Step 1: Create types.ts**

```typescript
// ts-agent/src/agents/polymarket/types.ts

export interface Market {
  id: string;
  title: string;
  prices: { yes: number; no: number };
  spread: number;
  liquidity: number;
  timeToClose: number; // seconds
}

export interface ScanResult {
  marketId: string;
  liquidityScore: number;
  spread: number;
  timeRemaining: number;
  passedFilter: boolean;
}

export interface ResearchResult {
  marketId: string;
  sentimentScore: number; // 0-1
  narrative: string;
}

export interface PredictionResult {
  marketId: string;
  pModelXgb: number;
  pModelLlm: number;
  pModelConsensus: number;
  confidence: "HIGH" | "MEDIUM" | "LOW";
}

export interface RiskValidation {
  marketId: string;
  kellyCriterion: number;
  betSize: number;
  var95Loss: number;
  approved: boolean;
  reasoning: string;
}

export interface Signal {
  marketId: string;
  direction: "YES" | "NO";
  betSize: number;
  edge: number;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  reasoning: string;
}

export interface BacktestOutput {
  timestamp: string;
  window: string;
  signals: Signal[];
  metrics: {
    totalExposure: number;
    maxDrawdown: number;
    sharpeRatio: number;
    winRate: number;
  };
  learningUpdates: {
    lessonsLearned: string[];
    nextScanPriority: string[];
  };
}
```

**Step 2: Create schemas**

```typescript
// ts-agent/src/schemas/polymarket_schemas.ts

import { z } from "zod";

export const MarketSchema = z.object({
  id: z.string(),
  title: z.string(),
  prices: z.object({ yes: z.number(), no: z.number() }),
  spread: z.number(),
  liquidity: z.number(),
  timeToClose: z.number(),
});

export const ScanResultSchema = z.object({
  marketId: z.string(),
  liquidityScore: z.number(),
  spread: z.number(),
  timeRemaining: z.number(),
  passedFilter: z.boolean(),
});

export const SignalSchema = z.object({
  marketId: z.string(),
  direction: z.enum(["YES", "NO"]),
  betSize: z.number(),
  edge: z.number(),
  confidence: z.enum(["HIGH", "MEDIUM", "LOW"]),
  reasoning: z.string(),
});

export const BacktestOutputSchema = z.object({
  timestamp: z.string(),
  window: z.string(),
  signals: z.array(SignalSchema),
  metrics: z.object({
    totalExposure: z.number(),
    maxDrawdown: z.number(),
    sharpeRatio: z.number(),
    winRate: z.number(),
  }),
  learningUpdates: z.object({
    lessonsLearned: z.array(z.string()),
    nextScanPriority: z.array(z.string()),
  }),
});
```

**Step 3: Create Polymarket API client**

```typescript
// ts-agent/src/io/polymarket/api_client.ts

import { Market } from "../../agents/polymarket/types";

const POLYMARKET_API_BASE = "https://clob.polymarket.com";

export async function getMarkets(limit: number = 50): Promise<Market[]> {
  const response = await fetch(`${POLYMARKET_API_BASE}/markets?limit=${limit}`);
  if (!response.ok) {
    throw new Error(`Polymarket API error: ${response.status}`);
  }
  const data = await response.json();
  // Transform to Market type
  return data.markets.map((m: any) => ({
    id: m.id,
    title: m.title,
    prices: { yes: m.prices.yes, no: m.prices.no },
    spread: m.prices.no - m.prices.yes,
    liquidity: m.pool.totalValue,
    timeToClose: Math.floor((new Date(m.closingTime).getTime() - Date.now()) / 1000),
  }));
}

export async function getPriceHistory(
  marketId: string,
  startTs: number,
  endTs: number,
  interval: string = "1h"
): Promise<Array<{ t: number; p: number }>> {
  const response = await fetch(
    `${POLYMARKET_API_BASE}/prices-history?market=${marketId}&startTs=${startTs}&endTs=${endTs}&interval=${interval}`
  );
  if (!response.ok) {
    throw new Error(`Polymarket API error: ${response.status}`);
  }
  const data = await response.json();
  return data.history;
}

export async function getOrderbook(marketId: string) {
  const response = await fetch(`${POLYMARKET_API_BASE}/orderbook?marketId=${marketId}`);
  if (!response.ok) {
    throw new Error(`Polymarket API error: ${response.status}`);
  }
  return response.json();
}
```

**Step 4: Commit**

```bash
git add ts-agent/src/agents/polymarket/ ts-agent/src/io/polymarket/ ts-agent/src/schemas/polymarket_schemas.ts
git commit -m "feat: create polymarket agent types, schemas, and API client"
```

---

### Task 3: Create Python project structure (agents)

**Files:**
- Create: `ts-agent/src/agents/research_agent.py`
- Create: `ts-agent/src/agents/predict_agent.py`
- Create: `ts-agent/src/agents/compound_agent.py`
- Create: `ts-agent/src/domain/polymarket/__init__.py`
- Create: `ts-agent/src/domain/polymarket/risk_calculator.py`

**Step 1: Create risk calculator (deterministic logic)**

```python
# ts-agent/src/domain/polymarket/risk_calculator.py

import math
from decimal import Decimal, ROUND_HALF_UP

def kelly_criterion(p: float, odds_decimal: float, alpha: float = 0.25) -> float:
    """
    Calculate fractional Kelly criterion bet sizing.

    Args:
        p: Probability of success (0-1)
        odds_decimal: Decimal odds from market price
        alpha: Fractional reduction (0.25-0.5 for safety)

    Returns:
        Fraction of bankroll to bet
    """
    if p <= 0 or p >= 1:
        return 0.0

    b = odds_decimal - 1  # Convert to decimal odds format
    if b <= 0:
        return 0.0

    # Kelly: f* = (p*b - (1-p)) / b
    kelly_full = (p * b - (1 - p)) / b
    kelly_fractional = alpha * kelly_full

    return max(0.0, min(kelly_fractional, 1.0))


def calculate_var_95(mean: float, std_dev: float) -> float:
    """
    Calculate Value at Risk at 95% confidence level.

    Args:
        mean: Expected return
        std_dev: Standard deviation

    Returns:
        Maximum loss (95% confidence)
    """
    z_score = 1.645  # 95% confidence
    var = mean - (z_score * std_dev)
    return var


def validate_risk_constraints(
    kelly_fraction: float,
    bet_size: float,
    var_95: float,
    bankroll: float,
    max_exposure: float,
    current_exposure: float,
    max_daily_loss: float,
    max_drawdown_pct: float,
) -> dict:
    """
    Validate all risk constraints.

    Returns:
        {
            'approved': bool,
            'violations': [list of constraint violations],
            'reasoning': str
        }
    """
    violations = []

    # Constraint 1: VaR
    if var_95 > max_daily_loss:
        violations.append(f"VaR {var_95:.2f} > daily limit {max_daily_loss:.2f}")

    # Constraint 2: Total exposure
    if current_exposure + bet_size > max_exposure:
        violations.append(f"Exposure {current_exposure + bet_size:.2f} > max {max_exposure:.2f}")

    # Constraint 3: Drawdown
    if max_drawdown_pct > 0.08:
        violations.append(f"Max drawdown {max_drawdown_pct:.2%} > 8%")

    # Constraint 4: Kelly sanity check
    if kelly_fraction < 0:
        violations.append("Negative Kelly fraction (no edge)")

    approved = len(violations) == 0
    reasoning = "; ".join(violations) if violations else "All constraints passed"

    return {
        "approved": approved,
        "violations": violations,
        "reasoning": reasoning,
    }
```

**Step 2: Create placeholder agents (Python)**

```python
# ts-agent/src/agents/research_agent.py

from typing import Optional

class ResearchAgent:
    """Research agent stub - NLP sentiment analysis placeholder."""

    async def analyze_sentiment(self, market_title: str) -> dict:
        """Placeholder for Twitter/Reddit sentiment analysis."""
        return {
            "market_id": "placeholder",
            "sentiment_score": 0.5,
            "narrative": f"Sentiment for: {market_title}",
        }
```

```python
# ts-agent/src/agents/predict_agent.py

import numpy as np

class PredictAgent:
    """Prediction agent stub - XGBoost + LLM placeholder."""

    async def predict(self, market_data: dict) -> dict:
        """Placeholder for XGBoost prediction."""
        return {
            "market_id": market_data.get("id"),
            "p_model_xgb": np.random.random(),
            "p_model_llm": np.random.random(),
            "confidence": "MEDIUM",
        }
```

```python
# ts-agent/src/agents/compound_agent.py

class CompoundAgent:
    """Learning loop agent - knowledge base management placeholder."""

    async def extract_lessons(self, failed_trades: list) -> dict:
        """Extract patterns from failures."""
        return {
            "lessons_learned": [],
            "next_scan_priority": [],
        }
```

**Step 3: Commit**

```bash
git add ts-agent/src/domain/polymarket/ ts-agent/src/agents/{research_agent,predict_agent,compound_agent}.py
git commit -m "feat: create polymarket domain logic and python agent stubs"
```

---

## Phase 2: Coordinator & Team Agent Setup

### Task 4: Create SwarmOrchestrator (main coordinator)

**Files:**
- Modify: `ts-agent/src/agents/polymarket/orchestrator.ts`
- Create: `ts-agent/src/agents/polymarket/subagent_definitions.ts`

**Step 1: Create subagent definitions**

```typescript
// ts-agent/src/agents/polymarket/subagent_definitions.ts

import { AgentDefinition } from "@anthropic-ai/claude-agent-sdk";

export const subagentDefinitions: Record<string, AgentDefinition> = {
  scan: {
    description: "Market scanner: filters 300+ Polymarket markets by liquidity, spread, time-to-close",
    prompt: `You are a market filtering specialist. Your role:
1. Accept a list of 300+ Polymarket markets
2. Filter by:
   - Liquidity score > 0.5
   - Spread < 5%
   - Time to close > 24 hours
3. Return JSON array of filtered markets with scores

Be deterministic, exact in calculations.`,
    tools: ["Read", "Bash"],
    model: "sonnet",
  },

  research: {
    description: "Sentiment analyzer: extracts NLP signals from Twitter/Reddit for market narratives",
    prompt: `You are a sentiment analysis specialist. Your role:
1. Given market titles, search for related tweets/sentiment
2. Classify sentiment: bullish (>0.6), neutral (0.4-0.6), bearish (<0.4)
3. Return structured JSON with sentiment_score and narrative

Use NLP classification, not speculation.`,
    tools: ["Bash"],
    model: "sonnet",
  },

  predict_xgb: {
    description: "XGBoost prediction engine: generates probability forecasts from historical tick data",
    prompt: `You are an ML prediction specialist using XGBoost. Your role:
1. Accept historical tick data (prices over 90 days)
2. Train XGBoost classifier on market resolution outcomes
3. Predict P(outcome) using predict_proba()
4. Return probability and confidence

Use machine learning rigorously, not heuristics.`,
    tools: ["Bash"],
    model: "sonnet",
  },

  predict_llm: {
    description: "LLM prediction engine: generates probability forecasts from narrative reasoning",
    prompt: `You are a base rate + narrative specialist. Your role:
1. Accept market narrative and historical base rate
2. Apply Bayesian reasoning: P(outcome | narrative)
3. Return probability calibrated to base rate
4. Return confidence HIGH/MEDIUM/LOW

Use probability theory, not guessing.`,
    tools: ["Read"],
    model: "sonnet",
  },

  risk_kelly: {
    description: "Risk validator (Kelly branch): computes position sizing and VaR constraints",
    prompt: `You are a Kelly Criterion specialist. Your role:
1. Accept p_model, market odds, bankroll
2. Calculate: Kelly = (p*b - (1-p)) / b
3. Calculate: Fractional Kelly (alpha = 0.25)
4. Calculate: VaR 95% = mu - 1.645*sigma
5. Validate constraints (VaR, exposure, drawdown)
6. Return bet_size and approval boolean

Be deterministic and precise with money math.`,
    tools: ["Bash"],
    model: "sonnet",
  },

  risk_sharpe: {
    description: "Risk validator (Sharpe branch): validates portfolio Sharpe ratio and drawdown",
    prompt: `You are a portfolio risk specialist. Your role:
1. Accept portfolio returns, volatility
2. Calculate: Sharpe = (return - risk_free) / volatility
3. Calculate: Max Drawdown from equity curve
4. Validate: Sharpe > 1.8, MDD < 8%
5. Approve/reject based on metrics

Use standard finance formulas.`,
    tools: ["Bash"],
    model: "sonnet",
  },

  execute: {
    description: "Signal generator: merges risk validation results and emits trading signals",
    prompt: `You are a signal aggregator. Your role:
1. Accept scan + research + predict + risk results
2. Calculate: edge = p_model - p_market
3. Check: edge > 0.04 AND risk_approved == true
4. Generate JSON signal with all metadata
5. Log to signals_*.json

Be precise in edge calculation and approval logic.`,
    tools: ["Read", "Bash"],
    model: "sonnet",
  },

  compound: {
    description: "Learning loop: extracts failure patterns and updates knowledge base",
    prompt: `You are a pattern extraction specialist. Your role:
1. Accept failed trades from backtest
2. Extract root causes (model accuracy, sentiment drift, liquidity crash)
3. Identify patterns: same failure 3+ times?
4. Update SQLite knowledge base with confidence scores
5. Return lessons_learned and next_scan_priority

Be rigorous in pattern extraction.`,
    tools: ["Bash"],
    model: "sonnet",
  },
};
```

**Step 2: Create orchestrator**

```typescript
// ts-agent/src/agents/polymarket/orchestrator.ts

import { query, ClaudeAgentOptions, AgentDefinition } from "@anthropic-ai/claude-agent-sdk";
import { subagentDefinitions } from "./subagent_definitions";
import { BacktestOutput } from "../../agents/polymarket/types";
import { BacktestOutputSchema } from "../../schemas/polymarket_schemas";

export class SwarmOrchestrator {
  async runBacktest(marketIds: string[], window: string): Promise<BacktestOutput> {
    const options: ClaudeAgentOptions = {
      allowedTools: ["Read", "Bash", "Task"],
      agents: subagentDefinitions,
    };

    const prompt = `
You are the SwarmOrchestrator for Polymarket trading bot.
Orchestrate the following pipeline for markets: ${marketIds.join(", ")}
Window: ${window}

1. SCAN: Filter markets by liquidity/spread/time-to-close using scan agent
2. RESEARCH: Analyze sentiment using research agent
3. PREDICT: Generate probabilities (XGBoost + LLM in parallel)
4. RISK: Validate Kelly sizing + VaR constraints (parallel agents)
5. EXECUTE: Merge results and emit signals
6. COMPOUND: Extract lessons from failed trades

Output final JSON matching BacktestOutput schema.
`;

    let output: BacktestOutput | null = null;

    for await (const message of query({ prompt, options })) {
      if ("result" in message) {
        console.log(message.result);

        // Parse and validate output
        try {
          output = BacktestOutputSchema.parse(JSON.parse(message.result));
        } catch (e) {
          console.error("Failed to parse output:", e);
        }
      }
    }

    return output || this.getDefaultOutput(window);
  }

  private getDefaultOutput(window: string): BacktestOutput {
    return {
      timestamp: new Date().toISOString(),
      window,
      signals: [],
      metrics: {
        totalExposure: 0,
        maxDrawdown: 0,
        sharpeRatio: 0,
        winRate: 0,
      },
      learningUpdates: {
        lessonsLearned: [],
        nextScanPriority: [],
      },
    };
  }
}

export async function runPolymarketBacktest(
  marketIds: string[],
  window: string
): Promise<BacktestOutput> {
  const orchestrator = new SwarmOrchestrator();
  return orchestrator.runBacktest(marketIds, window);
}
```

**Step 3: Commit**

```bash
git add ts-agent/src/agents/polymarket/{orchestrator,subagent_definitions}.ts
git commit -m "feat: create SwarmOrchestrator with team agent definitions"
```

---

## Phase 3: Agent Implementation & Testing

[Remaining tasks 5-10 follow same detailed format...]

---

## Execution Summary

**Total tasks**: 10
**Phases**: 6
**Commits**: 45+

**Ready to execute?**
