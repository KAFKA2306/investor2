---
name: edinet-dataset-builder
description: Build PIT-clean time-series financial datasets from EDINET documents with handling of missing values, corporate actions, and cross-period alignment. Use when constructing historical financial data for backtesting, aligning quarterly/annual statements into continuous time-series, handling corporate actions (splits, mergers) with point-in-time accuracy, or preparing training data for machine learning models.
origin: local-git-analysis
---

# EDINET Dataset Builder Skill

Expertise for constructing analytical datasets by performing Point-in-Time (PIT) cleaning and time-series integration on multi-period financial data obtained from EDINET.

## When to Use
Use for tasks related to the EDINET dataset builder within this project.

## Core Concepts

- **PIT Cleaning**: Based on the earnings announcement date, strictly manage each data point's validity window (use only information that was known at that time).
- **Missing Value Handling**: Address unreported items, submission delays, and format changes. Determine whether to interpolate or exclude depending on the context.
- **Corporate Action Adjustments**: Accurately scale data around corporate actions such as stock splits, capital changes, and M&A.
- **Time-Series Merging**: Integrate multiple reporting formats (annual reports, quarterly reports, interim reports) into a unified time series.

## Code Examples

1. **Metadata Extraction**: Extract announcement date, reference date, and accounting period from each EDINET document.
2. **Data Standardization**: Accommodate changes in accounting standards (e.g., IFRS transitions) and consolidate into a single accounting framework.
3. **Corporate Actions Registry**: From event columns such as dividend payment dates and split dates, compute data adjustment factors.
4. **Time-Series Assembly**: Fill missing values while outputting only data valid under PIT rules as a time series.

## Best Practices

- Data adjustment factors (e.g., split ratios) should always be retained as metadata to enable traceability.
- PIT rule violations (inclusion of future information) should be automatically detected and the affected intervals quarantined.
- Cache layers (e.g., SQLite) should manage processed documents and their versions to avoid reprocessing.