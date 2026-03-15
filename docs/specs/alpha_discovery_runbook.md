# Alpha Discovery Execution Runbook

This document provides the operational procedures for the alpha factor discovery process because systematic execution and knowledge capture are required to maintain competitive edge.

## Alpha Discovery Cycle

The process follows a continuous loop of hypothesis, execution, and validation because iterative refinement is the only way to isolate robust signals.

1. Theme Generation 🧠
Utilize advanced LLMs (e.g., Gemini 3.0 Pro) to generate novel investment themes because diverse perspectives are required to find orthogonal alpha in crowded markets.

2. DSL Generation 💻
Translate the investment theme into the Alpha DSL syntax because standardized code is mandatory for automated backtesting and verification.

3. Strict Validation 📈
Execute backtests using Point-In-Time (PIT) consistent data because look-ahead bias is the primary cause of false-positive alpha reports.

4. Knowledge Capture 📖
Update playbook.json and MEMORY.md with both successful signals and rejection rationales because the system must accumulate knowledge to prevent redundant future failures.
All rejections MUST be categorized using the 8-point system because structured data enables systematic improvement of the factor generation models.
Use logs to prevent redundant exploration because execution time is a scarce resource in the alpha discovery loop.

## Execution Commands

* Single Pass: task pipeline:discover
* Continuous Loop: task run:newalphasearch:loop

## Exception Handling

* Data Integrity (NaN): Per AAARTS protocols, missing data must propagate as NaN and trigger immediate rejection because corrupted inputs invalidate all downstream statistical significance.
* Domain Satiation: If the loop detects a series of identical or low-novelty candidates, the system should trigger a PIVOT because the current research domain has likely reached its information limit.
