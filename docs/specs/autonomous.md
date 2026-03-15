# Autonomous Operation Protocols

This document defines the boundaries of autonomous action for AI agents because clear limits are essential for system stability and human oversight.

## Operational Boundaries

Agents should operate within these defined limits because risk control is the primary constraint of autonomous trading.

1. Autonomous Actions (Low Impact)
Agents can generate new alpha factor DSL because creative exploration is a low-risk, high-reward activity.
Agents can perform analysis of backtest results because extracting insights from data is a core competency of AI.
Agents can execute defined Taskfile tasks because standardized tools ensure reproducible and safe research.
Agents can maintain documentation because clarity is essential for cross-agent synchronization.

2. Required Approvals (High Impact)
Agents must not modify capital allocation parameters without approval because financial risk must be governed by human oversight.
Agents must not modify system-level dependencies because uncontrolled infrastructure changes lead to unpredictable instability.
Agents must not change the core execution engine because structural integrity is the foundation of the trading platform.
Agents must not bypass CI gates because verification protocols are the only defense against code corruption.

## Escalation Criteria

Agents MUST escalate and notify a human operator immediately if any of the following conditions are met because catastrophic failures require external intervention:

* Upstream Failure: Persistent connectivity issues with J-Quants, EDINET, or e-Stat APIs because missing data halts the entire research pipeline.
* Systemic Anomalies: Detection of unrealistic performance metrics or infinite loops because machine hallucinations can lead to unintended order execution.
* Security Events: Unrecognized configuration changes or credential failures because system integrity is the highest security priority.
* Undefined Scenarios: Any situation not covered by existing workflows because agents must not improvise in high-stakes environments.

## Communication Standards
* Auditability: All autonomous decisions must be recorded in the Audit Log because traceability is mandatory for institutional compliance.
* Fail-Fast: Report errors immediately with full traceback because hidden failures delay critical resolution.
