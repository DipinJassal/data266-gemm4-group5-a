# LoRA (Bhoomika)

Train **only** on `harness/splits/train.txt` tasks — never `dev.txt`.
Weights are git-ignored; share them through a Kaggle dataset.

## Go / no-go (Nov 14, 2026): **GO**

A LoRA trained on the bf16 Gemma 4 31B loads and runs on the served QAT model in the official harness.

| Check | Result |
|---|---|
| Train on Kaggle | QLoRA (bf16 31B in 4-bit NF4), r16 / alpha 32 on all 7 linear projections of the language model (122M params), 8 steps on 4 train tasks, L4 x4. Loss 3.76 → 0.74. Peak memory ≤ 12 GiB per GPU. |
| Adapter format | PEFT `adapter_config.json` + `adapter_model.safetensors` (490 MB, 820 tensors). Keys `base_model.model.model.language_model.layers.N.…` match Kaggle's sample adapter exactly. |
| Loads on the served model | Harness run, 2 smoke tasks (`variants/bhoomika-lora-feasibility`, local only): vLLM started with `adapters=['main_lora','tool_lora']`, all 54 agent requests went to `main_lora`, no errors. **1/2 resolved**, 4.3 min per task. (2 tasks is a load test, not a score.) |
| Speed | Model load ~8 min. Training ~100 tokens/s: a 4K-token example ≈ 41 s per step, short ones 3–5 s. |
| GPU estimate | V1 (≈ 89 train tasks, 2 epochs, max 4K tokens): ≈ 1–1.5 h of L4 time ≈ **2–3 h of quota** per training run. Smoke run ≈ 2 h of quota, dev ≈ 5 h. |

## How to run training on Kaggle (lessons from the check)

- **L4 x4 needs the competition attached.** Without it, a kernel asking for `NvidiaL4` silently gets 2x T4 (15 GB each: OOM at 3K tokens).
- **Attaching the competition forces internet off** (Kaggle returns 400 on push otherwise). So packages are installed offline from:
  - `metric/gemma-4-developer-agent-wheelhouse` (bitsandbytes 0.46.1)
  - private dataset `bhoomikalnu/g5a-lora-wheels`: transformers 5.23.0 + its dependencies, peft 0.21.3, accelerate 1.15.0.
    The image's own transformers (5.0) does not know `gemma4`, so versions must be pinned.
- Use the official notebook's pinned Docker image (Python 3.12).
- Training data comes from private dataset `bhoomikalnu/g5a-lora-data` (`train_tasks.jsonl`: the 99 train-split tasks only).
- Model sources: `google/gemma-4/transformers/gemma-4-31b-it/1` (bf16, for training) and
  `google/gemma-4/Other/gemma-4-31b-it-qat-w4a16-ct/2` (served model: we use **its** tokenizer and chat template, which differ from the bf16 one).
- Both checkpoints are `Gemma4ForConditionalGeneration`; load the bf16 one with that class so PEFT keys get the `model.language_model.` prefix vLLM expects.
- Memory: `lm_head` is tied to the embeddings on GPU 0, so keep GPU 0 light (`max_memory` 6 GiB) and compute the loss in 512-token checkpointed chunks
  from the final hidden states (final logit softcapping = 30). Full 4K x 262K logits do not fit.
- Before shipping, rewrite `adapter_config.json` to the sample's key set with a plain `target_modules` list (vLLM-safe).

Files: `feasibility/train_tiny.py` (kernel script), `feasibility/kernel-metadata.json`, `feasibility/report_l4_run.json` (full report).
