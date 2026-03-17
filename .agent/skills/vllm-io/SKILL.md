---
name: vllm-io
description: MANDATORY TRIGGER: Invoke for any vLLM prompt/output integration task requiring parseable JSON/text, including chat template control, thinking-mode control, schema parsing, and runtime failure triage (JSONDecodeError, empty output, KV cache shortage, model-arch mismatch, CUDA symbol mismatch, multiprocessing startup errors).
origin: local-git-analysis
---

# vLLM I/O Skill

## When to Use
Use when working with vllm io related tasks.

## Objective
Produce deterministic, parseable output from vLLM with minimum moving parts.

## Core Concepts
- Use explicit role blocks with model chat tokens because mismatched templates lead to degradation in reasoning capability.
- End assistant prefix at the exact generation start point because extra whitespace or tokens can trigger unwanted "thinking" artifacts in JSON output.
- Prepend `<think>\n</think>\n` when structured output is required because this forces the model to skip verbose internal monologues and jump directly to the result.
- Keep one request per run during debugging because high-concurrency errors are difficult to distinguish from single-prompt failures on 12GB VRAM cards.

## Output Contract
- For JSON tasks, request exactly one JSON object because multi-object outputs break simple slicing logic and increase parsing latency.
- Extract output by slicing from first `{` to last `}` because LLMs often prepend or append conversational "chatter" that is not valid JSON.
- Validate required keys immediately because "silent" missing data results in downstream logic calculating with undefined values.
- Raise on missing keys or parse failure because an immediate crash is the only way to stop a corrupted alpha candidate from entering production.

## Standard Minimal Settings
- Start with `max_num_seqs=1`.
- Prefer `enforce_eager=True` for low-VRAM stability.
- Disable multimodal paths when text-only (`limit_mm_per_prompt={"image":0,"video":0}`).
- Keep context length small first, then increase only when required.

## Failure Triage Order
1. Empty/non-JSON output (vllm-io responsibility)
- Symptom: `JSONDecodeError` or blank text in valid model invocation.
- Action: constrain prompt to exact schema output and use `<think>\n</think>\n` assistant prefix.

2. KV cache exhaustion (vllm-io responsibility)
- Symptom: no available memory/cache blocks.
- Action: reduce model len, keep single sequence, keep eager mode.

3. Hardware/startup errors (→ delegate to qwen-local-inference)
- Symptom: CUDA symbol errors (`libcusparse`, `nvjitlink`), multiprocessing bootstrap RuntimeError, model architecture mismatch.
- Action: **See `qwen-local-inference` skill** for GPU initialization and process bootstrap handling.

**Note**: vllm-io scope is *after* successful model startup. Hardware-layer errors (CUDA, multiprocessing, model loading) are handled by `qwen-local-inference`.

## Code Examples
1. Build prompt.
2. Run one inference.
3. Parse and validate.
4. If fail, apply exactly one fix from triage order.
5. Re-run.

## Best Practices
- Single run returns parseable output.
- Required keys exist.
- Re-run with same prompt yields same output shape.
