---
name: fail-fast-coding-rules
description: >
  MANDATORY TRIGGER: Invoke BEFORE writing or reviewing any TypeScript/Python
  logic that could add error handling behavior. If the task includes try-catch,
  except, fallback return values, silent failure, retry-in-app, or stack trace
  loss concerns, this skill must be used to enforce crash-driven rules.
---

# Fail-Fast Coding Protocols (Crash-Driven Development)

This skill defines the operational standards for error handling, ensuring that failures are transparent, localized, and immediately actionable.

## 🚀 When to Use
- When implementing new business logic, algorithms, or data transformations.
- During code review to evaluate the validity of error-handling patterns.
- When debugging system behavior to ensure root causes are identified rapidly.

## 📖 Usage Instructions

### Implementation Strategy
- Input: Target functional logic.
- Procedure: 
    1. Implement the "happy path" cleanly and directly because complex nested logic is difficult to audit and verify.
    2. DO NOT catch and suppress exceptions within the logic layer because suppressed errors hide the root cause and delay system recovery.
    3. Allow the system to crash immediately upon encountering an invalid state because a visible crash is safer than a "silent" calculation error in quant trading.
- Output: Transparent code where failures produce clear stack traces and actionable feedback.

## 🛡️ Strict Rules

1.  DIE INSTANTLY: Throw exceptions immediately upon detecting an anomaly because data corruption must not propagate to the backtest or execution engine.
2.  NO `try-catch` IN BUSINESS LOGIC: Prohibit the use of `try-catch` blocks to mask potential failures because filters belong in the infrastructure, not the domain logic.
3.  REJECT DEFENSIVE FALLBACKS: Do not return "safe" defaults (e.g., `null`, `None`) to keep the system "running" because silent defaults create "Zombie Strategies" that lose money without reporting errors.

## Best Practices
- Separation of Concerns: Keep business logic pure; offload retries to the infrastructure layer because the domain layer should only focus on "what" to calculate, not "how" to recover from network drops.
- Descriptive Exceptions: Always include the context when raising an exception because a stack trace without a "Why" is a waste of a developer's time.
- Truth Over Smoothness: In quantitative finance, a crash is informative; a silent error is catastrophic because capital preservation depends on seeing the truth.
