---
name: polymarket-data-validation
description: >
  MANDATORY TRIGGER: Invoke for any task involving Polymarket data fetching, validation, and schema enforcement. If the request mentions Polymarket API, trades, positions, or Zod validation of market data, this skill must be used to enforce strict parsing and reject defensive coding practices.
---

# Polymarket Data Validation Skill

This skill defines the strict data fetching and validation protocol for Polymarket data streams.

## 🚀 When to Use
- When fetching user trades or positions from the Polymarket Data API.
- When validating external JSON payloads from Polymarket.
- When updating or enforcing Zod schemas for Polymarket entities.

## 📖 Usage Instructions

### 1. Schema Enforcement
- All Polymarket data structures MUST be modeled in `src/domain/market/polymarket_models.ts` using `zod`.
- No `any` types. No untyped objects.

### 2. Fetching Strategy
- The fetcher (`src/io/market/polymarket_fetcher.ts`) must hit the API and immediately pass the response to the Zod schema for parsing.
- NO `try-catch` blocks around the fetch or parse logic. 
- Fast failures preserve stack traces.

### 3. Execution
- Use `task polymarket:validate` or `bun src/scripts/validate_polymarket_data.ts` to test parsing logic against live data.

## 🛡️ Iron Rules

1.  NO SAFETY NETS: NEVER write defensive `try-catch` blocks. The code must crash loudly if the API response deviates from the defined schema.
2.  ZOD ONLY: `Pydantic` for Python, `Zod` for TS/Bun. No plain objects.
3.  STRICT IO/DOMAIN SPLIT: Validation schemas belong in `domain`. The `fetch()` invocation belongs in `io`.
