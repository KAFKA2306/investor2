# 自律的クオンツ・アルファ生成パイプライン（理想的ロードマップ）

**目的**: 本ドキュメントの目的は、自律的かつ高性能なアルファ生成システムの理想アーキテクチャを明確化することである。  
**背景**: 将来の機能を整理し、プロジェクトが完全自律へ向かう明確な開発ロードマップを維持する。

## 要約
本ドキュメントは、Gemini が自律的にアルファ・シグナルを発見・検証・適用する理想的パイプラインを概説する。過去の記憶、堅牢な市場データ処理、専門的な基盤モデルを統合し、コスト意識の高い投資パフォーマンスを一貫して実現する。本設計図は、システムの進化に対する指針として機能する。

---

## 自律的クオンツ・アルファ生成パイプライン（理想フロー）

本ダイアグラムは、標準運用を前提としたターゲットアーキテクチャを概説する。

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

## 構造的強化
1. 記憶主導の探索である。過去の成功と失敗を探索サイクルの主要なシードとして活用する。  
2. 早期アーカイブである。中間候補を記録し、長期的な知識ベースを構築する。  
3. 共設計アーキテクチャである。取引ロジック、アルファ因子、ポートフォリオ配分を相互依存的に設計し、相乗効果を最大化する。  
4. 反復的学習である。すべての却下および実行の更新をメタレイヤへフィードバックし、将来のサイクルを改善する。

## ロードマップ要件（未解決目標）
1. データ品質ゲートである。欠損データ、レイテンシ、リーク検出の明示的な閾値を定義し、低忠実度の学習を防止する。  
2. 厳密な検証ルールである。シャープ比、情報比（IC）、最大ドローダウン、およびコスト控除後のパフォーマンスの受理基準を形式化する。  
3. 配分制約である。セクター集中度、流動性制約、および売買回転予算に関する厳格な規則を実装する。  
4. 適応的リーニングである。漸化分析に基づく自動再学習またはモデル切替のトリガを確立する。

---

## コア発見ループ（最小フロー）
> 詳細仕様については、`docs/specs/alpha_discovery_runbook.md`を参照する。

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