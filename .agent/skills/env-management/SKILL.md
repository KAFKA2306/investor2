---
name: env-management
description: >
  MANDATORY TRIGGER: Invoke BEFORE any task that reads, writes, or debugs
  environment and config values (.env, API keys, model names, base URLs, path
  config, or credential lookups). If the request mentions OPENAI_API_KEY,
  OPENAI_BASE_URL, FRED_API_KEY, EDINET_API_KEY, J-Quants tokens, missing key,
  config error, or any secrets/path change, this skill must be used first.
---

# Environment Management Skill (MANDATORY HOOK)

This skill ensures the secure management of environment variables and project configurations.

## 🚀 When to Use
- When defining new environment variables.
- When handling secrets (e.g., API keys, database passwords).
- When verifying or modifying global project configurations (Non-secrets).
- IMPORTANT: This skill must be invoked BEFORE performing any work related to environment variables.

## 📖 Usage Instructions

### Secret Management
- Input: New credentials or API keys.
- Procedure: DO NOT edit `.env` directly; update `.env.example` and request user input because committing secrets to version control is a catastrophic security failure.
- Output: Securely configured environment.

### Non-Secret (Configuration) Management
- Input: Model names, risk parameters, directory paths, etc.
- Procedure: Define these in `config/default.yaml` because centralized configuration ensures that the entire agent fleet operates under a unified set of rules.
- Output: Integrated and consistent configuration across the project.

## 🛡️ Iron Rules

1.  NO PERSISTENT LOGGING OF SECRETS: Never print secrets to the console or logs because telemetry data is often stored in plain text and can be compromised.
2.  NO HARDCODING: Never embed API keys or sensitive paths directly in source code because hardcoded values break environment portability and leak credentials.
3.  VALIDATION: Always implement presence and type checks when loading configuration values because invalid configurations cause unpredictable system behavior and "silent" failures.
4.  GIT HYGIENE: Ensure `.env` is listed in `.gitignore` and never committed because file leakage is the most common path for credential theft.

## Best Practices
- Config Schema: Use Zod or Pydantic to strictly validate configurations at runtime because type-safe configurations prevent logic errors before the application logic even starts.
- Variable Naming: Use project-specific prefixes (e.g., `UQTL_`) to avoid namespace collisions because generic names may be overwritten by system environment variables.
