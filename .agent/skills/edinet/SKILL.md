---
name: edinet
description: Retrieve and parse Japanese EDINET financial documents (annual/quarterly reports) with ticker mapping and risk extraction. Use when sourcing Japanese equity data, extracting regulatory filings for PIT-clean datasets, identifying material risks from 10-K equivalents, or enriching J-Quants data with fundamental context. Pair with edinet-dataset-builder for time-series construction.
origin: local-git-analysis
---

# Edinet Financial Document Retrieval Skill

Expert knowledge for efficiently obtaining and analyzing financial documents such as securities reports from EDINET (Electronic Disclosure for Investors' NETwork) provided by Japan's Financial Services Agency.

## When to Use
Use when working with EDINET-related tasks in this project.

## Core Concepts
- **Document Type (DocType)**: Securities Report (Annual), Quarterly Report, Extraordinary Report.
- **Search Logic**: Convert securities codes to EDINET codes using `edinet_tickers.ts`, with date range specification.
- **Analytical Considerations**: The difficulties of XBRL parsing, noise removal during text extraction, and structuring of unstructured data.

## Code Examples
1. **Ticker Mapping**: Retrieve the EDINET-specific code from a securities code (e.g., 7203).
2. **Metadata Fetch**: Retrieve the list of filings submitted within a specific period and filter for material events (M&A, partnerships, etc.).
3. **Deep Extraction**: Use an LLM to extract specific items (e.g., business risks, management policies) from PDF/XBRL.

## Best Practices
- To avoid overloading the API, prioritize using caching mechanisms such as `jquants_cache_warm.ts`.
- If document retrieval fails, retry using exponential backoff.