# AAARTS: Autonomous Agentic Alpha Research Trade System

## Introduction

AAARTS is a quantitative trading and research system designed as an integrated intelligence cycle, handling everything from alpha hypothesis generation to backtesting and validation. The system is currently focused on corporate earnings forecasting research using Japanese securities reports (EDINET) for submission to NeurIPS 2026.

## Research Status

* **Strategy Dashboard**: [AAARTS Strategy OS](https://kafka2306.github.io/investor2/)
* **EDINET-Bench Evaluation**: Actively evaluating performance on financial fraud detection and directional earnings forecasting tasks.
* **Ablation Study**: Systematically isolating the predictive power of quantitative financial ratios versus qualitative textual disclosures in regulatory filings.
* **OOS Governance**: Alpha candidates require frozen chronological out-of-sample evidence before promotion.
* **Multi-paper OOS Suite**: Four additional classic papers and seven paper–factor hypotheses are evaluated with a locked post-publication protocol.
* **Strategy ontology**: Versioned strategies connect hypotheses, implementations, research runs, evidence, gates, decisions, mutations, and trade boundaries.
* **Execution boundary**: Portfolio and execution records are GO-only; no live orders are sent by the dashboard.

## Key Pointers

* **NeurIPS Paper Outline**: [docs/paper/neurips_earnings_forecast_outline.md](docs/paper/neurips_earnings_forecast_outline.md)
* **System Flowchart**: [docs/diagrams/simpleflowchart.md](docs/diagrams/simpleflowchart.md)
* **Alpha Discovery Runbook**: [docs/specs/alpha_discovery_runbook.md](docs/specs/alpha_discovery_runbook.md)
* **Time-Tested Alpha Policy**: [docs/specs/time_tested_alpha_policy.md](docs/specs/time_tested_alpha_policy.md)
* **Momentum OOS Example**: [docs/research/post_publication_momentum_oos.md](docs/research/post_publication_momentum_oos.md)
* **Multi-paper OOS Results**: [docs/research/multi_paper_oos_summary.md](docs/research/multi_paper_oos_summary.md)
* **Paper–Factor Registry**: [docs/research/paper_factor_registry.json](docs/research/paper_factor_registry.json)
* **Strategy Registry**: [docs/research/strategy_registry.json](docs/research/strategy_registry.json)
* **Strategy Ontology**: [src/ontology.ts](src/ontology.ts) · [ADR-005](docs/adr/005-aaarts-strategy-dashboard-ontology.md)
* **Strategy Registry Builder**: [scripts/build_strategy_registry.py](scripts/build_strategy_registry.py)
* **2010s Paper Catalog**: [docs/research/2010s_paper_catalog.md](docs/research/2010s_paper_catalog.md)
* **Operational Rules**: [AGENTS.md](AGENTS.md)
* **Architectural Decision Records (ADRs)**: [docs/adr/](docs/adr/)

## Setup and Execution

### Setup
```bash
task setup
cp .env.example .env
uv sync
```

### Run
```bash
task run:newalphasearch  # Start autonomous alpha search loop
task view                # Start the dashboard and API

# Rebuild the strategy-centered machine-readable registry
python3 scripts/build_strategy_registry.py

# Validate the registry through the Zod ontology
./node_modules/.bin/tsx -e 'import { readFileSync } from "node:fs"; import { StrategyRegistrySchema } from "./src/ontology.ts"; StrategyRegistrySchema.parse(JSON.parse(readFileSync("docs/research/strategy_registry.json", "utf8"))); console.log("ontology: PASS");'
```

---

*This repository conforms to harness engineering standards as specified in ADR-001.*
