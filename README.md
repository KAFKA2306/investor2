# AAARTS: Autonomous Agentic Alpha Trade System

## Introduction

AAARTS is a quantitative trading and research system designed as an integrated intelligence cycle, handling everything from alpha hypothesis generation to backtesting and validation. The system is currently focused on corporate earnings forecasting research using Japanese securities reports (EDINET) for submission to NeurIPS 2026.

## Research Status

*   **EDINET-Bench Evaluation**: Actively evaluating performance on financial fraud detection and directional earnings forecasting tasks.
*   **Ablation Study**: Systematically isolating the predictive power of quantitative financial ratios versus qualitative textual disclosures in regulatory filings.

## Key Pointers

*   **NeurIPS Paper Outline**: [docs/paper/neurips_earnings_forecast_outline.md](docs/paper/neurips_earnings_forecast_outline.md)
*   **System Flowchart**: [docs/diagrams/simpleflowchart.md](docs/diagrams/simpleflowchart.md)
*   **Operational Rules**: [AGENTS.md](AGENTS.md)
*   **Architectural Decision Records (ADRs)**: [docs/adr/](docs/adr/)

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
```

---

*This repository conforms to harness engineering standards as specified in ADR-001.*