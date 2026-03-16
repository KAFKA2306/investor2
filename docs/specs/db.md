# Unified Database (Postgres) Specification

This document defines the Postgres architecture that serves as the primary home for the quant system because high-concurrency and relational integrity are required for professional trading.

## Schema Configuration

Data is organized into 8 schemas because logical isolation prevents namespace collisions and simplifies access control.

| Schema | 説明 | 実装状態 | 用途 |
|---|---|---|---|
| **ref** | Reference Data | ⚠️ 計画中 | Master data for instruments and venues because global identifiers must be consistent across all layers. |
| **ingest** | Ingest Data | ⚠️ 計画中 | Raw data from external providers because uninterpreted data must be preserved for audit. |
| **research** | Research Data | ⚠️ 計画中 | Processed documents and sentiment scores because research efficiency depends on pre-parsed text. |
| **feature** | Feature Store | ⚠️ 計画中 | Calculated alpha source features because versioned features are required to prevent signal decay analysis errors. |
| **signal** | Signal Data | ⚠️ 計画中 | Strategy intentions and signal lineage because the system must record the "Family Tree" of every decision. |
| **eval** | Evaluation Data | ⚠️ 計画中 | Backtest results and outcome analysis because profitability is the only metric that matters for verification. |
| **exec** | Execution Data | ⚠️ 計画中 | Orders and fills because execution quality must be audited against market impact. |
| **obs** | Observability | ⚠️ 計画中 | Audit logs and system events because observability is the primary defense against systemic failure. |

### Current Implementation Status

As of 2026-03-17, Postgres integration is in **Phase 2: Dual Write** with compat schema for legacy compatibility. All schemas are planned but not yet in production use.

**Recommendation**: Consult `config/default.yaml` for current SQLite cache locations, which remain the operational source of truth during the transition period.

## Integration Phases

1. Phase 1: Read Compatibility [DONE]
Create the compat schema because legacy agents require a familiar view during the migration period.

2. Phase 2: Dual Write [IN PROGRESS]
Execute writes to both SQLite and Postgres because data redundancy ensures safety during the cutover.

3. Phase 3: Primary Cutover
Switch Postgres to the master position because centralized management is the long-term goal.

4. Phase 4: Full Transition
Retire legacy SQLite writes because system complexity must be minimized once Postgres is stable.

## Development Rules

- Type Safety: Use PostgresClient with Strict TypeScript because type errors must be caught at compile time.
- Naming: Use snake_case because it is the industry standard for Postgres.
- Traceability: Maintain source_doc_id links because every feature must be traceable to its original disclosure.

Owner: Antigravity Quant Team
Status: Postgres Integration Spec v1.0
