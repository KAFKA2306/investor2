---
name: qwen-local-inference
description: >
  MANDATORY TRIGGER: Invoke for any local LLM inference task using Qwen/vLLM on
  GPU, including alpha idea generation, JSON-schema constrained output, OpenAI
  API replacement, local model benchmarking, or vLLM troubleshooting. If the
  request mentions local model, Qwen, vLLM, GPU inference, or avoiding external
  API cost, this skill must be used.
---

# Qwen Local Inference Skill

This skill leverages Qwen 3.5 9B for rapid, secure, and cost-effective intelligence generation, specifically optimized for alpha factor discovery.

## 🚀 When to Use
- When generating novel quantitative investment ideas or themes.
- When utilizing local GPU resources (CUDA) for high-speed inference.
- When requiring strictly formatted JSON output for downstream pipelines.

## 📖 Usage Instructions

### Running Inference
- Input: System prompt, user prompt, and target JSON schema.
- Procedure: 
    1. Select the appropriate engine: `vLLM` (recommended) because it offers significantly higher throughput for batch alpha generation.
    2. Resolve the model path using `path_utils.py` because model locations can change across different GPU servers.
    3. Execute the inference script.
- Output: A validated JSON object conforming to the specified schema.

## 🛡️ Iron Rules

1.  Dynamic Path Resolution: NEVER hardcode model paths because hardcoded strings break the inference loop when containers or volumes are remounted.
2.  Fail-Fast Execution: DO NOT use `try-catch` blocks in business logic because hidden inference errors lead to empty or "hallucinated" alpha files that corrupt the knowledgebase.
3.  Schema Validation: All LLM outputs MUST be validated using Zod or Pydantic because LLMs occasionally fail to follow formatting rules, and malformed JSON will crash the downstream orchestrator.

## 🚀 Inference Engines
- vLLM (Recommended): Optimized for high throughput and parallel idea generation.
- Transformers (Fallback): Used for flexibility in hardware-constrained environments.

## 🔧 Qwen 3.5 Operational Troubleshooting (Verified: 2026-03-07)

### Error Matrix and Resolutions

| Error | Root Cause | Fix |
|-------|------------|-----|
| `KeyError: 'qwen3_5'` | Stable vLLM version lacks `qwen3_5` architecture registration. | Install Nightly vLLM. |
| `ImportError: libcusparse ... undefined symbol` | Version mismatch between `cu129 torch` and system CUDA libraries. | Prepend the `.venv` nvjitlink path to `LD_LIBRARY_PATH`. |
| `No available memory for the cache blocks` | Vision Encoder profiling overhead or insufficient VRAM (12GB). | Apply the optimized `LLM()` parameter set below. |
| `JSONDecodeError` (Empty output) | Thinking mode consumes entire `max_tokens` budget. | Prepend `<think>\n</think>\n` to the assistant prompt. |

### Nightly vLLM Installation (Mandatory)
```bash
uv pip install -U vllm --torch-backend=auto --extra-index-url https://wheels.vllm.ai/nightly
```
> Note: Avoid `uv run` for this execution as it may overwrite the nightly build. Execute directly via `.venv/bin/python`.

### Optimized LLM() Configuration (12GB VRAM Minimum)
```python
llm = LLM(
    model=model_path,
    gpu_memory_utilization=0.9,
    max_model_len=4096,           # Default (262144) exceeds 12GB VRAM
    enforce_eager=True,           # Disable torch.compile to save memory
    limit_mm_per_prompt={"image": 0, "video": 0},  # Disable Vision Encoder profiling
    enable_chunked_prefill=False, 
    max_num_seqs=1,
)
```

### Thinking Mode Disablement Prompt Pattern
```python
prompt = (
    f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
    f"<|im_start|>user\n{user_prompt}<|im_end|>\n"
    f"<|im_start|>assistant\n<think>\n</think>\n"   # Forces immediate JSON output
)
```

### Execution Example
```bash
LD_LIBRARY_PATH=/home/kafka/finance/investor/.venv/lib/python3.12/site-packages/nvidia/nvjitlink/lib:$LD_LIBRARY_PATH \
/home/kafka/finance/investor/.venv/bin/python llm/qwen3.5-9b/ace_qwen_verify.py
```
