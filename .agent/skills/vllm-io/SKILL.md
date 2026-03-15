---
name: vllm-io
description: MANDATORY TRIGGER: Invoke for any vLLM prompt/output integration task requiring parseable JSON/text, including chat template control, thinking-mode control, schema parsing, and runtime failure triage (JSONDecodeError, empty output, KV cache shortage, model-arch mismatch, CUDA symbol mismatch, multiprocessing startup errors).
---

# vLLM I/O Skill

## Objective
Produce deterministic, parseable output from vLLM with minimum moving parts.

## Input Contract
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
1. Model/API mismatch
- Symptom: unknown architecture, unsupported args.
- Action: use a Qwen3.5-compatible vLLM build and remove unsupported constructor args.

2. CUDA library mismatch
- Symptom: `libcusparse` or `nvjitlink` symbol errors.
- Action: prepend `.venv` nvjitlink path to `LD_LIBRARY_PATH`.

3. KV cache exhaustion
- Symptom: no available memory/cache blocks.
- Action: reduce model len, keep single sequence, keep eager mode.

4. Empty/non-JSON output
- Symptom: `JSONDecodeError` or blank text.
- Action: constrain prompt to exact schema output and use `<think>\n</think>\n` assistant prefix.

5. Multiprocessing bootstrap error (WSL)
- Symptom: spawn bootstrapping RuntimeError.
- Action: wrap entrypoint with `if __name__ == '__main__':`.

## Run Pattern
1. Build prompt.
2. Run one inference.
3. Parse and validate.
4. If fail, apply exactly one fix from triage order.
5. Re-run.

## Done Criteria
- Single run returns parseable output.
- Required keys exist.
- Re-run with same prompt yields same output shape.
