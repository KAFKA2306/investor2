# Unified Database (Postgres) Specification

This document defines the Postgres architecture that serves as the primary home for the quant system because high-concurrency and relational integrity are required for professional trading.

## Schema Configuration

Data is organized into 8 schemas because logical isolation prevents namespace collisions and simplifies access control.

1. ref (Reference Data)
Master data for instruments and venues because global identifiers must be consistent across all layers.

2. ingest (Ingest Data)
Raw data from external providers because uninterpreted data must be preserved for audit.

3. research (Research Data)
Processed documents and sentiment scores because research efficiency depends on pre-parsed text.

4. feature (Feature Store)
Calculated alpha source features because versioned features are required to prevent signal decay analysis errors.

5. signal (Signal Data)
Strategy intentions and signal lineage because the system must record the "Family Tree" of every decision.

6. eval (Evaluation Data)
Backtest results and outcome analysis because profitability is the only metric that matters for verification.

7. exec (Execution Data)
Orders and fills because execution quality must be audited against market impact.

8. obs (Observability)
Audit logs and system events because observability is the primary defense against systemic failure.

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
