# Autonomous Quant Alpha Generation Pipeline (Ideal Roadmap)

**Objective**: Clarify the ideal architecture for an autonomous and high-performance alpha generation system.
**Context**: To organize future features and ensure the project maintains a clear development path toward full autonomy.

## Executive Summary
This document maps the "Ideal Pipeline" where Gemini autonomously discovers, validates, and deploys alpha signals. It integrates historical memory, robust market data handling, and specialized foundational models to achieve consistent, cost-aware investment performance. This blueprint serves as the north star for the system's evolution.

---

## Autonomous Quant Alpha Generation Pipeline (Ideal Flow)

This diagram outlines the target architecture for standard operations.

```mermaid
flowchart TD
    subgraph MetaLayer [Meta Layer (Control Center)]
        MemoryMgmt["Memory Management (Historical Context)"]
        StateMonitor["State Monitoring"]
        RequirementInput["Strategic Requirements"]
        SeedSelection["Seed Factor Selection"]
        StateMonitor --> |Update| MemoryMgmt
        MemoryMgmt --> SeedSelection
        RequirementInput --> SeedSelection
    end

    subgraph DataLayer [Data Engineering Layer]
        DataHarvesting["Data Collection (EDINET/J-Quants/e-Stat)"] --> DataIntegration["Data Unified Processing"]
        DataIntegration --> DataVetting{"Data Quality Check✨"}
        DataVetting -- "Pass" --> ScenarioGen["Context/Scenario Generation"]
        DataVetting -- "Fail" --> DataIntegration
    end

    subgraph ResearchPhase [Research & Verification Phase]
        KnowledgeRef["Foundational Knowledge Ref"] --> FactorSearch["Factor Discovery (Alpha Search)"]
        SeedSelection --> |Input| FactorSearch
        ScenarioGen --> |Contextual Input| FactorSearch
        FactorSearch --> |Mutation/Structural Update| CandidateGen["Candidate Generation"]
        DataIntegration --> CandidateGen
        CandidateGen -.-> |Archive Candidates| MemoryMgmt
        CandidateGen --> StrategyDesign["Strategy Design (Logic/Alpha AST/Allocation)"]
        StrategyDesign --> ModelSelection["Model Selection (Time-series/Text/Multimodal)"]
        ModelSelection --> AdaptationDesign["Adaptation Policy (LoRA/Prompting/Constraints)"]
        AdaptationDesign --> Verification["Verification (Co-optimization/Backtest)"]
        ModelSelection -.-> |Save Configuration| MemoryMgmt
        Verification -- "Fail" --> Rejection["Rejection Archive"]
        Verification -- "Pass" --> VerificationVetting{"Verification Pass?"}
        VerificationVetting -- "PASS" --> SelectionVerdict{"Selection Verdict (Sharpe/IC/MDD)"}
        VerificationVetting -- "Data Error" --> DataIntegration
        VerificationVetting -- "Model Error" --> ModelSelection
        Verification -.-> |Save Verification Results| MemoryMgmt
        SelectionVerdict -- "REJECT" --> Rejection
        SelectionVerdict -.-> |Save Verdict| MemoryMgmt
        
        Rejection -.-> |Learnings Feedback| MemoryMgmt
    end

    subgraph ExecutionPhase [Execution & Audit Phase]
        SelectionVerdict -- "ACCEPT" --> OrderGate{"Order Pre-Check Gate"}
        OrderGate -- "Pass" --> AllocationOpt["Allocation Optimization"]
        OrderGate -- "Fail" --> Rejection
        AllocationOpt --> RiskControl["Risk Management"]
        RiskControl --> HedgeOpt["Hedge Optimization"]
        HedgeOpt --> OrderGen["Order Generation"]
        OrderGen --> Execution["Execution (Deploy)"]
        OrderGen -.-> |Save Order Plan| MemoryMgmt
        Execution -.-> |Save Fills| MemoryMgmt
        Execution --> PerformanceAudit["Performance Auditing"]
        PerformanceAudit --> DriftAnalysis["Drift/Slippage Analysis"]
        DriftAnalysis -.-> |Report Status| StateMonitor
        PerformanceAudit -.-> |Performance Feedback| MemoryMgmt
    end

    DataLayer --> ResearchPhase
    ResearchPhase --> ExecutionPhase
```

## Structural Enhancements 💡
1. **Memory-Driven Search**: Uses historical success and failure as the primary seed for discovery cycles.
2. **Early Archiving**: Captures intermediate candidates to build a long-term knowledge base.
3. **Co-design Architecture**: Designs trading logic, alpha factors, and portfolio allocation co-dependently to maximize synergy.
4. **Iterative Learning**: Every rejection and execution update feeds into the Meta Layer to improve future cycles.

## Roadmap Requirements (Outstanding Goals)
1. **Data Quality Gates**: Define explicit thresholds for data missingness, latency, and leak detection to prevent low-fidelity training.
2. **Rigorous Verification Rules**: Formalize acceptance criteria for Sharpe, IC, MDD, and net-of-costs performance.
3. **Allocation Constraints**: Implement strict rules for sector concentration, liquidity limits, and turnover budgets.
4. **Adaptive Re-learning**: Establish triggers for automatic re-training or model switching based on drift analysis.

---

## 🎀 Core Discovery Loop (Minimal Flow)
> Refer to `docs/specs/alpha_discovery_runbook.md` for detailed specifications.

```mermaid
flowchart TD
    A[task run / run:newalphasearch] --> B[Loop Cycle Start]
    B --> C[Theme Generation (LLM)]
    C --> D[Validate/Backtest]
    D --> E[Score (Fitness/Novelty/Stability/Adoption)]
    E --> F{Is Idea Novel?}
    F -- No --> C
    F -- Yes --> G[Update Memory/ACE]
    G --> H[Append Unified Log]
    H --> I[Save Cycle Plot]
    I --> J{Failure Limit Reached?}
    J -- No --> B
    J -- Yes --> K[Auto Stop]
```
