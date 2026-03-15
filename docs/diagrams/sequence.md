# Autonomous Quant Logic Sequence (Operational Ideal)

**Objective**: Establish a structural blueprint for the interaction between agents, from alpha generation to order execution.
**Context**: To eliminate operational ambiguity and create a fully autonomous, self-improving pipeline.

## Executive Summary
This document outlines the interaction cycle between Gemini 3.0 Pro and specialized agents. It covers the end-to-end process: idea generation, Point-In-Time (PIT) data curation, AST-based strategy design, and Net-of-Costs backtesting. This recipe ensures every second of computation is directed toward discovering and deploying valid alpha.

---

## Autonomous Quant Logic Sequence (Ideal Architecture)

This diagram represents the localized standard for high-autonomy operations.

```mermaid
sequenceDiagram
    autonumber
    actor User as Human Operator 🐣
    participant Orch as Orchestrator 🎀
    participant Mem as Memory Core 📖
    participant Data as Data Engineer 🛠️
    participant Res as Quant Researcher 🧪
    participant Exec as Execution Agent 🚀

    Note left of Orch: Phase 1: Discovery & Contextualization 🔍
    User->>Orch: Input requirements
    Orch->>Mem: Retrieve historical context
    Mem-->>Orch: Provide seeds and exclusion zones (failure history)
    Orch->>Orch: Generate initial context (mission/constraints/memory/data/evaluation)
    Orch->>Orch: Generate hypothesis & factor ideas 💡
    Orch->>Mem: Save candidate ideas
    Orch->>Data: Request PIT-consistent dataset
    Data-->>Orch: Provide training dataset and context
    Orch->>Orch: Validate data quality
    alt Data Quality Fail
        Orch->>Data: Request data regeneration
        Data-->>Orch: Provide revised dataset
        Orch->>Orch: Re-validate data
    else Data Quality Pass
        Orch->>Orch: Proceed to evaluation
    end
    Orch->>Mem: Commit data version and preprocessing parameters
    
    Note left of Orch: Phase 2: Evaluation & Verification ⚖️
    Orch->>Res: Dispatch candidate formula and dataset
    Res->>Res: Design Trading Logic / Alpha AST / Allocation Strategy
    Res->>Res: Select Foundation Model and Adaptation Policy
    Res->>Res: Search for factors and validate formula
    Res->>Res: Execute Net-of-Costs Backtest
    Res-->>Orch: Return Strategy Pack (AST/Trading Rules/Allocation/KPIs) 🎁
    Orch->>Orch: Evaluate against success criteria
    alt Logic Error (Data Source)
        Orch->>Data: Re-request dataset with corrections
        Data-->>Orch: Revised dataset
        Orch->>Res: Re-evaluate
    else Logic Error (Model Configuration)
        Orch->>Res: Request model reconfiguration
        Res-->>Orch: New model configuration
        Orch->>Res: Re-evaluate
    else Criteria Met (PASS)
        Orch->>Orch: Proceed to final vetting
    end
    Orch->>Mem: Save verification results and model configuration
    
    Note right of Orch: Final Vetting & Execution 💓
    
    alt Strategy Accepted 🎉
        Orch->>Orch: Final pre-trade check (constraints/expiry/capacity)
        alt Execution GO
            Orch->>Exec: Generate orders
            Exec->>Exec: Execute and capture fills
            Exec-->>Orch: Report execution results
            Orch->>Mem: Record Order Plan / Execution / Audit / Drift
        else Execution HOLD
            Orch->>Mem: Record HOLD reason (capacity limit, etc.)
        end
    else Strategy Rejected (PIVOT) 😢
        Orch->>Mem: Record rejection rationale and performance metrics
    end
```

## Structural Enhancements 💡
1. **Pre-emptive Context**: Orchestrator aligns requirements and history before execution to minimize redundant computation.
2. **Knowledge Archival**: Candidates are saved early to enable later retrieval and "cross-pollination" of ideas.
3. **Reproducibility**: Preprocessing parameters are versioned alongside data to ensure consistent backtest results.
4. **Integrated Design**: Trading logic, alpha, and allocation are designed co-dependently to maximize total system performance.
5. **Value in Rejection**: Rejection rationales are treated as high-value data for the next search iteration.

---

## 🎯 Core Alpha Discovery Loop (Operational Minimum)
> See `docs/specs/alpha_discovery_runbook.md` and `docs/specs/autonomous.md` for details.

```mermaid
sequenceDiagram
    autonumber
    participant A as antigravity/codex
    participant T as Taskfile
    participant L as Loop Supervisor
    participant O as Gemini/Qwen (Idea Gen)
    participant V as Validation/Backtest
    participant M as memory/ACE
    participant U as unified log
    participant P as plot writer

    A->>T: Invoke with UQTL_INPUT_CHANNEL + UQTL_NL_INPUT
    T->>L: run:newalphasearch:loop
    L->>O: Generate next discovery theme
    O-->>L: theme + feature_signature + idea_hash
    L->>V: Execute validation and generate score
    V-->>L: fitness/novelty/stability/adoption
    L->>L: Orthogonality Check (novelty + hash + signature)
    alt No Novelty
        L->>O: Regenerate theme
    else Novelty Pass
        L->>M: Update theme/progress/policy
        L->>U: Append alpha_discovery log
        L->>P: Save cycle plot
        P-->>L: Plot update complete
    end
    L->>L: Check failure threshold (Ralph Loop)
```
