---
name: finmcp-analyst-workflows
description: >
  MANDATORY TRIGGER: Invoke for real-time AI trader evaluation tasks across live
  markets (US/CN/crypto), including autonomy benchmarking, leaderboard updates,
  live-news validation, contamination-free protocol design, and risk/profit
  performance checks. If the request asks to validate, benchmark, or test an AI
  trader in real or near-real conditions, this skill must be used.
---

# AI-Trader Real-Time Verification Skill

This skill is designed to evaluate how autonomously an AI agent can perform in "live" market conditions, providing a rigorous benchmark for operational readiness.

## 🚀 When to Use
- When testing an AI trader's "combat readiness" and generating performance rankings.
- When measuring true capability by avoiding data contamination (ensuring the agent only acts on real-time information).
- When validating autonomy across multiple asset classes, including US equities, Chinese equities, and Cryptocurrencies.

## 📖 Usage Instructions

### Running Real-Time Benchmarks
- Input: AI agent inference engine, target markets, and verification window.
- Procedure: 
    1. Register the AI agent in the "Combat Arena" because a standardized environment is required for fair performance comparison.
    2. Monitor real-time news retrieval and the validity of agent actions because out-of-date information leads to "stale" investment decisions.
    3. Collect and score trading outcomes because profitability is the ultimate verification of an agent's intelligence.
- Output: A multi-dimensional evaluation report covering profitability and risk.

## 🛡️ Strict Rules

1.  Data-Contamination Free: NEVER use future data or historical data present in the AI's training set because "hindsight bias" artificially inflates performance and leads to live-trading failure.
2.  Search & Verify: Always cross-reference news and external data because LLM hallucinations can create "phantom" market events that don't exist in reality.
3.  Multi-Market Consistency: Performance must be stable across diverse environments because an alpha that only works in one market is likely an artifact of overfitting.

## Best Practices
- Real-Time Leaderboards: Visualize performance rankings because friendly competition and transparency accelerate the "happy" engineering cycle.
- Gen 4 Feedback: Use weaknesses identified during verification to inform future designs because failure is the most efficient teacher for engineering evolution.
