# Operational Governance Dashboard Specification

**最終更新**: 2026-03-17 | **実装状況**: ⚠️ 部分実装

**Objective**: Ensure decision-making quality and safety in autonomous trading through comprehensive observability and control.
**Context**: To address concerns regarding alpha validity, adherence to trading rules, and traceability of decision reasoning.

---

## 📋 実装状況サマリー

### ✅ 実装済み (Section A: Core Dashboard)

| 機能 | ファイル | 行数 | 状態 |
|---|---|---|---|
| HTTP Server (Hono) | `src/dashboard/server.ts` | 1328 | ✅ 実装 |
| キャッシュ統計表示 | `src/dashboard/server.ts:stats` | - | ✅ 実装 |
| 企業情報一覧 | `src/dashboard/server.ts:companies` | - | ✅ 実装 |
| 企業情報詳細 | `src/dashboard/server.ts:company/:id` | - | ✅ 実装 |
| スクリーナー | `src/dashboard/server.ts:screener` | - | ✅ 実装 |
| XBRL 表示 | `src/dashboard/server.ts:xbrl` | - | ✅ 実装 |

### 🔮 Aspirational (Section B: Advanced Features)

- Alpha Discovery View（新アルファ候補表示）— 未実装
- Kill Switch（取引即時停止）— 未実装
- Execution Management View（ポジション・リスク管理）— 未実装
- Performance Audit View（パフォーマンス監査）— 未実装
- Risk Guardian（リスク警告・サーキットブレーカー）— 未実装
- History & Rejection View（採択/却下履歴）— 未実装

---

## Executive Summary

### ✅ 実装済み: Core Dashboard Infrastructure

This dashboard currently provides **observation and data visualization** for cache statistics, company information, and market screening.

Built with `Hono` (Node.js/Bun HTTP framework), it serves:
- Real-time cache statistics
- Company fundamental data from EDINET
- Market screener with multi-factor filtering

### 🔮 Aspirational: Advanced Governance Features

The following sections describe the **planned future state** (見積 2026年Q2) where the dashboard will leverage reasoning capabilities to provide end-to-end alpha discovery governance—from candidate identification through execution and auditing.

---

## 1. Objectives
The dashboard provides three primary functional layers for operational control:

- **Rapid Candidate Selection**: Evaluate and filter newly discovered alpha factors.
- **Reliable Execution Control**: Enforce trading rules and risk limits during deployment.
- **Comprehensive Audit Trace**: Record all decision rationales to ensure full traceability.

## 2. Personas
- **Operational Manager**: PMs, Risk Managers, and Team Leads responsible for system oversight.
- **Trading Desk**: Operators responsible for execution monitoring and manual intervention.
- **Compliance & Audit**: Officers responsible for verifying regulatory and internal rule adherence.

## 3. Core Principles
- **Total Visibility**: A single unified view for all critical system states.
- **Process Integrity**: Forced adherence to the Discovery -> Evaluation -> Execution -> Audit sequence.
- **Evidence-Based**: Distinction between raw data metrics and model-based reasoning.
- **Rejection Archival**: Mandatory recording of rejection rationales for all non-selected candidates.
- **Pre-Trade Validation**: Hard gates for risk limits and circuit breakers prior to order execution.
- **Granular Traceability**: Direct drill-down from UI metrics to source-level logs.

## 4. Operational Sequence (Workflows)

```mermaid
sequenceDiagram
    autonumber
    participant User as Operator
    participant DB as Dashboard UI
    participant AS as Alpha Searcher
    participant EX as Execution Engine
    participant AU as Audit Log Schema 1.1.8

    User->>DB: Open Dashboard
    DB->>AS: Request latest alpha candidates
    AS-->>DB: Candidate list and evaluation scores
    User->>DB: Drill-down into metrics
    DB->>DB: Display quality gate status
    User->>DB: Promote candidate to selection
    DB->>EX: Send execution allocation
    EX-->>DB: Execution status
    DB->>AU: Commit decision rationale (Audit Trace)
```

## 5. UI Layout Structure
```mermaid
flowchart TD
    StatusBar["Top: System Status Bar"]
    DiscoveryView["Discovery: Alpha Factor Factory"]
    FinancialView["Financial: Core Metrics (Taskfile Compliant)"]
    EvaluationView["Evaluation: Reasoning & Metric Rationale"]
    ExecutionView["Execution: Allocation & Risk Gates"]
    AuditView["Audit: P&L & Execution Performance"]
    HistoryView["History: Rejection Archive & Updates"]

    StatusBar --> DiscoveryView
    StatusBar --> FinancialView
    StatusBar --> EvaluationView
    StatusBar --> ExecutionView
    StatusBar --> AuditView
    StatusBar --> HistoryView
```

## 6. Functional Sections

### 6.1 Status Bar — ✅ 実装済み
- Visual indicator for system "Vitality" (Active/Suspended).
- Real-time alerts for anomaly detection and timestamp of last data heartbeat.
- **実装**: `src/dashboard/server.ts` のヘッダーセクション

### 6.2 Alpha Discovery View — 🔮 未実装
- Displays `Expected Alpha` and `Recency` of new candidates.
- Prioritization based on proprietary score with "MISSING" indicators for incomplete inputs.
- **計画**: Layer 3 Signal 実装時に統合予定（2026年Q2見積）

### 6.3 Financial Metrics View (FINANCIAL Tab) — ⚠️ 部分実装
- Truthful representation of `task run` outputs without ad-hoc interpolation.
- KPI Cards: `gross_return`, `net_return`, `total_cost_bps`, `fee_bps`, `slippage_bps`, `sharpe_ratio`, `max_drawdown`, `volatility`, `cagr`, `win_rate`, `profit_factor`, `information_ratio`, `information_coefficient`.
- Charts: Dual-axis comparison of `net_return` and `basket_daily_return`.
- Tabular data for stage-specific metrics (`benchmark`, `investment_outcome`).
- **現状**: キャッシュ統計のみ実装。Full pipeline metrics は未実装

### 6.4 Quantitative Evaluation View — 🔮 未実装
- Benchmarking of `Sharpe`, `MDD`, and other ratios against defined targets.
- Visual comparative analysis of "Target" vs. "Actual" performance.
- **計画**: Layer 3 Signal + backtest integration 時に実装（2026年Q2見積）

### 6.5 Execution Management View — 🔮 未実装
- Symbol-level `Allocation` suggestions.
- Hard-coded logic to block orders exceeding risk budgets or positional limits.
- `Kill Switch` for immediate order cancellation and order suspension.
- **計画**: Layer 4 Portfolio implementation 時に追加（2026年Q2見積）

### 6.6 Performance Audit View — 🔮 未実装
- Realized P&L tracking and cumulative return visualization.
- Slippage analysis and fill-rate auditing to evaluate execution quality.
- **計画**: Layer 5 Memory + execution data integration 時に実装（2026年Q2見積）

### 6.7 History & Rejection View — 🔮 未実装
- Historical archive of rejection reasons for non-selected alpha.
- Audit log of parameter updates and configuration changes (User Attribution).
- **計画**: Layer 5 Memory + playbook integration 時に実装（2026年Q2見積）

## 7. Key Features
1. **Candidate Scoring**: Rank-ordered alpha discovery results.
2. **Financial KPI Visualization**: Comprehensive Return/Risk/Cost/Efficiency metrics.
3. **Benchmark Comparison**: Real-time delta between targets and results.
4. **Rejection Factor Management**: Data-driven tracking of rejection rationales.
5. **Dynamic Allocation Suggestions**: Risk-budgeted allocation proposals.
6. **Pre-Trade Control**: Guardian logic to prevent rule-violating orders.
7. **Kill Switch**: Instant suspension of all execution capabilities.
8. **P&L Auditing**: Real-time and realized loss/profit tracking.
9. **Execution Quality Analytics**: Quantitative analysis of implementation shortfall.
10. **Data Traceability**: Direct link from dashboard metrics to audit logs.
11. **Parameter Change Log**: Immutable record of operational rule updates.
12. **Status Management**: 3-stage lifecycle for strategy state (Research, Staging, Active).
13. **Classification Management**: Clear separation between committed and forecasted data.

## 8. Monitored Indicators
- **Expected Return**: `Expected Alpha`
- **Realized P&L**: `Realized P&L`
- **Maximum Drawdown**: `Maximum Drawdown`
- **Volatility**: `Volatility`
- **Allocation Ratio**: `Allocation Ratio`
- **Slippage**: `Implementation Shortfall`
- **Turnover**: `Turnover`

## 9. UI/UX Standards
- **3-Click Rule**: Critical operations must be accessible within 3 interactions.
- **Modal-less Verification**: Seamless drill-down without context switching.
- **Safety First**: Perpetual visibility and access to the Emergency Kill Switch.

## 10. Data Governance Rules
- **Real-Time Threshold**: Data latency must not exceed 60 seconds.
- **Absolute Integrity**: No interpolation for missing data. Display as "MISSING".
- **Immutability**: Historical records are write-once, read-many (Immutable).
- **Missing Value Policy**: Explicit use of `MISSING` or `INVALID`. No ad-hoc use of `0` or `UNKNOWN`.
- **Error Visibility**: Silent failures are prohibited. Data contract violations must be surfaced on-device.

## 11. Acceptance Criteria
- End-to-end alpha discovery-to-selection workflow must reside within the dashboard.
- All candidate rejections must be traceable to defined rationales.
- Pre-trade risk gates must be mandatory and non-bypassable.
- Every metric must be traceable to its original raw log event.
- Strategy state must be explicitly managed through the 3-stage lifecycle.

## 12. Strategy Selection Logic
```mermaid
flowchart LR
    Inputs["Observation Data"] --> Analysis["Feature/Hypothesis Generation"]
    Analysis --> Verdict{"Decision Logic"}
    Verdict -- Promote --> Execution["Rebalancing Execution"]
    Verdict -- Hold --> Observe["Additional Observation/Validation"]
    Verdict -- Pivot --> Redesign["Model/Domain Redesign"]
```

## 13. Roadmap

### ✅ 完了 (2026-03-17)
1. ✅ Core HTTP server with cache stats, company info, screener

### 🔮 計画 (見積 2026年Q2)
1. 🔮 Alpha Discovery View integration (Layer 3 Signal 実装時)
2. 🔮 Implement Risk Guardian + Kill Switch (Layer 4 Portfolio 実装時)
3. 🔮 Finalize Performance Audit and History layers (Layer 5 Memory 実装時)
4. 🔮 Validate compliance with all defined acceptance criteria

## 14. Data Lifecycle Model (Mermaid)
Dashboard consumes `investor.log-envelope.v2` units, validated by `kind` and schema version.

```mermaid
erDiagram
    CANONICAL_LOG_ENVELOPE {
      string schema "investor.log-envelope.v2"
      string id
      string runId
      string kind
      string asOfDate
      datetime generatedAt
      bool derived
    }

    DAILY_DECISION {
      string date
      string analyzedAt
      string verdict
      string strategy
      string action
    }

    BENCHMARK_PAYLOAD {
      string date
      string stageName
      string status
    }

    INVESTMENT_OUTCOME {
      string date
      string stageName
      string status
    }

    QUALITY_GATE {
      string verdict "NOT_READY|CAUTION|READY"
      number score "0..100"
      datetime generatedAt
    }

    CONNECTIVITY_STATUS {
      string provider "jquants|estat|kabucom|edinet"
      string status "PASS|FAIL|SKIP|MISSING"
    }

    ALPHA_DISCOVERY_V3 {
      string schema "investor.alpha-discovery.v3"
      string date "YYYYMMDD"
      string stage "DISCOVERY_PRECHECK"
      string scoreType "LINGUISTIC_PRECHECK"
      number sampleSize
      number selectedCount
      number selectionRate
    }

    ALPHA_CANDIDATE {
      string id
      string description
      string reasoning
      string status "SELECTED|REJECTED"
      string rejectReason "Refer to REASON_DESC.md for details"
      datetime recency
      number priority "0..1"
      number plausibility "0..1"
      number riskAdjusted "0..1"
      number novelty "0..1"
    }

    CANONICAL_LOG_ENVELOPE ||--o| DAILY_DECISION : "kind=daily_decision"
    CANONICAL_LOG_ENVELOPE ||--o| BENCHMARK_PAYLOAD : "kind=benchmark"
    CANONICAL_LOG_ENVELOPE ||--o| INVESTMENT_OUTCOME : "kind=investment_outcome"
    CANONICAL_LOG_ENVELOPE ||--o| QUALITY_GATE : "kind=quality_gate"
    CANONICAL_LOG_ENVELOPE ||--o| ALPHA_DISCOVERY_V3 : "kind=alpha_discovery"

    QUALITY_GATE ||--|{ CONNECTIVITY_STATUS : "connectivity"
    ALPHA_DISCOVERY_V3 ||--|{ ALPHA_CANDIDATE : "candidates"
```

### 14.1 Operational Integrity Rules
- Do NOT mask missing data with `0` or `UNKNOWN`.
- `Discovery` stage metrics must be strictly isolated from post-backtest metrics.
- Connectivity check results from `quality_gate` are the primary health indicators.
- Schema-violating logs are rejected and flagged as `Data Contract Violations`.

## 15. Metrics and Charting Model
Dual-mode presentation of raw snapshots and aggregated time-series.

```mermaid
erDiagram
    METRIC_DEFINITION {
      string metricKey "e.g., selection_rate, net_return"
      string label
      string unit "pct|bps|count|status"
      number minValue
      number maxValue
      bool nullable
      string sourceKind
      string sourcePath
    }

    METRIC_SNAPSHOT {
      string asOfDate "YYYYMMDD"
      string metricKey
      number value
      string status "VALID|MISSING|INVALID"
      datetime generatedAt
    }

    CHART_DEFINITION {
      string chartId
      string title
      string chartType "line|bar|area|table|chip"
      string xField
      string yField
      string nullPolicy "show-missing"
    }

    CHART_SERIES {
      string chartId
      string seriesKey
      string metricKey
      string colorToken
      string aggregation "last|sum|avg|none"
    }

    CHART_POINT {
      string chartId
      string seriesKey
      string asOfDate
      number yValue
      string pointStatus "VALID|MISSING|INVALID"
      string provenanceId
    }

    METRIC_DEFINITION ||--o{ METRIC_SNAPSHOT : generates
    CHART_DEFINITION ||--|{ CHART_SERIES : contains
    CHART_SERIES ||--o{ CHART_POINT : maps_to
    METRIC_DEFINITION ||--o{ CHART_SERIES : references
```

### 15.1 Core Metric definitions
- `selection_rate`: Selection efficiency (0..1).
- `net_return`: Realized net return (pct).
- `total_cost_bps`: Aggregate implementation cost (bps).
- `sharpe_ratio`: Risk-adjusted returns (ratio).
- `jquants_status`: Connectivity with J-Quants API (status).

### 15.2 Mandatory `task run` Metrics
Metrics required for the integrated discovery-benchmark-analysis-execution pipeline:
- **Returns**: `gross_return`, `net_return`, `basket_daily_return`, `cumulative_return`, `cagr`.
- **Risks**: `sharpe_ratio`, `max_drawdown`, `volatility`, `win_rate`, `information_ratio`, `information_coefficient`.
- **Costs**: `fee_bps`, `slippage_bps`, `total_cost_bps`.
- **Efficiency**: `expected_edge`, `profit_factor`, `avg_return`, `trading_days`.

## 16. Deprecation Policy
- Only `investor.log-envelope.v2` and higher schemas are supported.
- Legacy `readiness` indicators are deprecated in favor of `quality_gate`.
- Programs masking errors or bypassing data contract validations are strictly prohibited.
- Detected contract violations must be surfaced in the `Data Contract Violations` view.
