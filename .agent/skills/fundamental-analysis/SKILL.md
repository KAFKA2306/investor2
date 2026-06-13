---
name: fundamental-analysis
description: Fundamental analysis and macro-top-down investing framework for detecting dividend traps, sentiment/fundamentals divergences, and cash flow quality issues. Use when conducting equity research with macro regime context, screening for dividend safety risks, detecting mean-reversion opportunities in mispriced fundamentals, or auditing cash flow quality before investment decisions.
origin: local-git-analysis
---

# Fundamental & Macro Analysis Skill

Expertise in analyzing macroeconomic indicators, evaluating a company's fundamentals, and auditing market sentiment.

## When to Use
Use when working on fundamental analysis related tasks in this project.

## Core Concepts
- **Macro Top-Down (Macroeconomics)**:
  - **Key Indicators**: CPI (inflation), policy rate, GDP growth, and employment statistics.
  - **Regime Transitions**: identifying inflationary, deflationary, and stagflation environments.
  - **Asset Correlations**: detection of abnormal correlations among equities, bonds, gold, and oil (simultaneous upswings or simultaneous declines).
- **Fundamental Audit (Fundamental Audit)**:
  - **Yield Traps**: identifying stocks with high dividend yields but excessively high payout ratios or insufficient cash flows.
  - **Sentiment Discrepancy**: fundamentals are strong, yet the stock is undervalued due to excessive market pessimism.
  - **Cash Flow Analysis**: evaluation of the health of operating cash flow and free cash flow.

## Code Examples
1. **Macro Scanning**: Determining the current economic phase based on data sources such as FRED and the ECB.
2. **Correlation Mapping**: Detecting distortions in correlations across asset classes and seeking mean-reversion trading opportunities.
3. **Sentiment vs Fundamentals Audit**: Extracting inconsistencies between news, social media (SNS), analyst reports, and financial statements.
4. **Safety Check**: warnings on dividend cuts for high-yield stocks and on highly indebted companies.

## Best Practices
- Macro analysis should always be benchmarked against past similar cases to confirm historical repeatability.
- Do not rely solely on surface metrics like the P/E ratio or the P/B ratio; prioritize cash flow quality.
- When sentiment is extremely negative, always formulate the contrarian hypothesis: why might the market be wrong?