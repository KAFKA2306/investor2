---
name: fred-economic-data
description: >
  MANDATORY TRIGGER: Invoke for any request involving FRED macro data, including
  GDP, CPI, unemployment, rates, yield curve, PCE, economic calendars, regime
  detection, or macro features for quant models. If the user asks for FRED
  series IDs, macro time-series pulls, or historical/current macro comparisons,
  this skill must be used before any data fetch.
---

# FRED Economic Data Access Skill

This skill enables rapid access to over 800,000 economic time-series data points (GDP, unemployment, inflation, etc.) from FRED for comprehensive macro analysis.

## 🚀 When to Use
- When fetching the latest macro-economic indicators (e.g., GDP, CPI, interest rates).
- When analyzing market regimes by comparing historical economic data.
- When monitoring economic release schedules to time trading strategies.

## 📖 Usage Instructions

### Economic Data Retrieval
- Input: Series ID, observation period, and transformation method.
- Procedure: 
    1. Ensure `FRED_API_KEY` is set in the environment because missing credentials will cause the data fetch to fail.
    2. Use the `FREDQuery` class to query the desired series because centralized access logic ensures consistent error handling and rate limit compliance.
    3. Perform frequency aggregation as required because macro indicators must be aligned with equity market timeframes (e.g., daily) for correlation analysis.
- Output: Structured time-series data containing date-value pairs.

## 🛡️ Strict Rules

1.  API Key Management: NEVER hardcode the API key; access it via environment variables because source code is shared and security must be preserved.
2.  Rate Limit Compliance: Do not exceed FRED API request limits because being blacklisted from FRED will disable the entire macro research pipeline.
3.  Data Validation: Proactively handle missing or malformed data because FRED datasets often contain "placeholder" characters like "." that crash standard numerical parsers.

## Best Practices
- Regime Switch Detection: Capture shifts in inflation or interest rates because global macro regimes are the primary driver of market-wide risk.
- Visualization: Use descriptive plotting to visualize macro trends because human-in-the-loop verification is required for high-stakes investment decisions.
- Data Fidelity: Prefer PIT (Point-In-Time) data for realistic backtesting because revised economic data (e.g., GDP revisions) creates look-ahead bias if used carelessly.
