---
name: edinet-dataset-builder
description: >
  MANDATORY TRIGGER: Invoke for any EDINET-related workflow, including Japanese
  filing download, XBRL/TSV parsing, financial statement extraction, dataset
  labeling, and EDINET-Bench replication. If the request mentions EDINET,
  Japanese filings, XBRL, or fundamental dataset building, this
  skill must be used immediately.
---

# EDINET Dataset Builder Skill

This skill provides the operational framework for collecting financial filings from the Japanese EDINET system and building high-quality machine learning datasets (EDINET-Bench).

## 🚀 When to Use
- When bulk downloading financial reports (Security Reports, Quarterly Reports) from Japanese corporations.
- When extracting and structuring corporate financial data (e.g., Balance Sheets, Income Statements) or non-financial text blocks.
- When constructing custom datasets for quantitative tasks such as fraud detection, earnings forecasting, or industry classification.

## 📖 Usage Instructions

### Report Retrieval and Parsing
- Input: Target company identifiers, observation period (start_date/end_date), and target extraction categories.
- Procedure: 
    1. Use `downloader.py` to fetch identifying documents to local storage because raw XBRL files must be available for offline validation.
    2. Employ `parser.py` to extract target items from TSV/XBRL formats because LLMs require structured text to perform sentiment or fundamental analysis.
- Output: Structured financial and textual data in TSV or JSON format.

## 🛡️ Strict Rules

1.  API Key Compliance: Ensure the `EDINET_API_KEY` is correctly configured in the environment because unauthorized access or missing credentials will terminate the data fetch pipeline.
2.  Path Management: Adhere to the `where-to-save` guidelines because saving large datasets to the D-drive is mandatory to prevent local filesystem disk-full crashes.
3.  Fail-Fast Principle: Do not attempt to bypass or silently "fix" parsing errors because malformed data leads to "garbage-in/garbage-out" scenarios that invalidate alpha signals.

## Best Practices
- EDINET-Bench Replication: Utilize standard scripts under `scripts/` to reproduce benchmark datasets because consistent baselines are required to measure model improvement.
- LLM Integration: For complex tasks like fraud detection, automate labeling by pipe-lining extracted text to LLM prompts because the semantic nuances of financial filings require intelligent interpretation.
- Fidelity over Coverage: Prioritize the accuracy of parsed financial fields over total filing coverage because one high-quality signal is more valuable than a thousand noisy ones.
