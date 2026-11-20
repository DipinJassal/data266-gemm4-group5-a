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

## V1: LoRA on reference patches (Nov 14, 2026)

Variant: `variants/bhoomika-lora-patches-v1` = `dipin-step-budget-v1` (4.5 min / 50 tool calls) + a trained `main_lora`.

**Data** (`v1/prepare_data.py`, Kaggle CPU kernel `g5a-lora-v1-data`): each train-split task's reference patch becomes one agent
trajectory on the real repo snapshot, in the harness's exact prompt and tool format: `grep` for a name from the issue → `read_file`
around each hunk → one `edit_file` per hunk → `py_compile` → `submit_patch` → short summary. Every trajectory is checked to reproduce
the reference patch. Smoke tasks are held out. 88 train / 9 held-out examples; 13 longer than 10,240 tokens were dropped → **75 trained**.

**Training** (`v1/train_v1.py`, run with `python lora/v1/push_v1.py train`, kernel `g5a-lora-v1-train`): QLoRA on bf16 31B, r16 / alpha 32,
all 7 linear projections, 1 epoch, LR 1e-4, loss only on tool calls and the final answer. 82 min on L4 x4.
Held-out loss **1.158 → 0.400**. Report: `v1/v1_train_report.json`.

**Results** (dev baseline 2/30; the control `dipin-step-budget-v1` scored 2/10 on smoke and has no dev score yet):

| Adapter strength | Smoke (10) | Dev (30) | Notes |
|---|---|---|---|
| alpha 32 (as trained) | 1/10, 1/10 (two runs) | — | Agent stops thinking, reads tiny file windows, guesses edits, repeats a failing `edit_file` up to 14 times. |
| **alpha 8 (1/4 strength, shipped)** | **2/10**, 1 empty patch | **5/30 = 16.7%**, 4 empty, avg 3.4 min | fastapi 3/15, rich 2/11, requests 0/3, httpx 0/1. |

**Lessons**
- Templated trajectories have no thinking and no error recovery, so a full-strength adapter overfits to "always succeed on the first edit".
  Lowering alpha keeps the formatting benefit (fewer empty patches) without the brittleness. V2 trains on real agent runs for this reason.
- Harness race: `run_kaggle.py` can push the kernel before the new `g5a-agents` dataset version is ready, so a run silently uses the previous
  upload. Always check the run's `agent/adapters/main_lora/adapter_config.json` in the outputs.
- 5/30 equals Khushi's V1 (also built on the control). Until the control has a dev score, neither gain can be credited to the change alone.
