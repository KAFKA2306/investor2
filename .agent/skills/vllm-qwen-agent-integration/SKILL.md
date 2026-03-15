---
name: vllm-qwen-agent-integration
description: MANDATORY TRIGGER: Invoke when replacing OpenAI API usage with local vLLM-served Qwen3.5-9B in existing agents, including OPENAI_BASE_URL/OPENAI_MODEL wiring, provider-style alignment, end-to-end validation, and troubleshooting integration failures across config, endpoint format, and runtime behavior.
---

# vLLM Qwen Agent Integration Skill

## Goal
Replace OpenAI endpoint dependency in agent workflows with local vLLM Qwen3.5-9B, without changing agent call sites.

## Preconditions
- Local model files exist under `llm/qwen3.5-9b/models/...`.
- vLLM runtime works on the current GPU.
- `OpenAIThemeProvider` supports OpenAI-compatible endpoint switching.

## Integration Contract
- Keep provider class usage unchanged in agents because modifying core agent logic for every backend change introduces regression risks and technical debt.
- Switch backend by environment only because hardcoded provider names prevent seamless switching between Local GPU and Cloud Fallbacks.
- Use OpenAI-compatible API surface because this allows us to leverage standard SDKs and existing prompt templates without redesign.

## Required Environment
Set in repo-root `.env`:
- `OPENAI_BASE_URL=http://127.0.0.1:8000/v1`
- `OPENAI_MODEL=Qwen/Qwen3.5-9B`
- `OPENAI_API_KEY=EMPTY`
- `OPENAI_API_STYLE=chat_completions`

If provider auto-detect is trusted, `OPENAI_API_STYLE=auto` is acceptable.

## Runtime Steps
1. Start local vLLM server for Qwen3.5-9B.
2. Export/confirm the environment variables above.
3. Run agent workflow via Taskfile entry point.
4. Verify output is non-empty and parseable at agent boundary.

## Verification Steps
1. Provider smoke test: one prompt, one response.
2. Agent path test: run one existing agent that depends on `OpenAIThemeProvider`.
3. Pipeline test: run one minimal task that exercises theme generation.
4. Confirm logs show local endpoint and expected model name.

## Failure Triage
1. 401/403 or disabled provider
- Check `OPENAI_API_KEY` exists (use `EMPTY` for local), confirm env loaded.

2. 404 endpoint mismatch
- Provider style and server endpoint disagree.
- Set `OPENAI_API_STYLE=chat_completions` for vLLM unless responses API is confirmed.

3. Empty output / parse failure
- Enforce stricter output instructions and JSON contract at prompt boundary.

4. vLLM startup/runtime failure
- Apply `vllm-io` and `qwen-local-inference` skills for GPU/memory/CUDA fixes.

## Done Criteria
- Existing agent classes run unchanged.
- Requests hit local vLLM endpoint.
- Expected output schema or text contract is satisfied in at least one end-to-end run.
