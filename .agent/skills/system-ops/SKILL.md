---
name: system-ops
description: Runtime config management, telemetry logging, and quality gate criteria for alpha factor auditing. Use when deploying agents in production, configuring environment variables for different execution modes, monitoring pipeline health via telemetry, auditing alpha factors against CDD standards, or enforcing architectural layer boundaries in runtime systems.
origin: local-git-analysis
---

# System Operations & Runtime Skill

Expertise in runtime configuration, telemetry, and quality management for financial analytics systems.

## When to Use
Use when working with system ops related tasks in this project.

## Core Concepts
- **Runtime Config**: Multi-layered configuration management using `default.yaml` and environment variables.
- **Telemetry**: I/O logging using `telemetry_logger.ts` and artifact storage in `CanonicalLog` format.
- **Quality Gate**: Quality criteria for alpha factors based on backtest scores, correlations, and orthogonality.

## Code Examples
1. **Startup**: Environment initialization, database connection, and cache warm-up via `app_runtime_core.ts`.
2. **Execution Gate**: Pre- and post-execution quality checks via `quality_gate.ts`.
3. **Persistance**: Persistence of analysis results in the `investor.log-envelope.v2` format.

## Knowledge Inheritance Process (Knowledge Inheritance Process)
In this project, knowledge is transferred from code to `SKILL.md` through the following cycle to keep the code clean.

1. **Discovery**: Experiment with new logic or prototypes in `src/experiments/`.
2. **Standardization**: Integrate successful logic into `BaseAgent` and `UnifiedProvider`.
3. **Extraction**: Document and preserve domain-specific quirks, parameter tuning tips, and failure patterns encountered during implementation in `.agent/skills/*/SKILL.md`.
4. **Pruning**: Remove legacy experimental code and duplicate agent implementations once migration to `SKILL.md` is complete.
5. **Inheritance**: The LLM loads these `SKILL.md` through `loadSkillKnowledge()` before task execution and uses past knowledge as prior knowledge.

## Best Practices
- Environment variables should be standardized with the `UQTL_` prefix and managed centrally in `runtime_config.ts`.
- Test data and caches should be redirected to `/root/.gemini/tmp/` or the project's `.cache/` directory to avoid polluting the source code.
- Experimental logic should be implemented by extending `BaseAgent`, and successful ones should be added as knowledge in `SKILL.md`; remove unnecessary code.