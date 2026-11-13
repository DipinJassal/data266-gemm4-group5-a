"""LoRA feasibility check (Bhoomika). Runs INSIDE a Kaggle GPU kernel (NvidiaL4 x4, internet ON for pip).

Trains a tiny QLoRA adapter for a few steps on the bf16 Gemma 4 31B (loaded in 4-bit), using 4 train-split tasks,
then saves it in the exact layout the competition harness expects (adapters/<name>/adapter_config.json +
adapter_model.safetensors, keys `base_model.model.model.language_model.layers.N...`).

Answers the go/no-go questions:
  1. Does Gemma 4 31B fit for QLoRA training on 4x L4, and how long does a step take? (-> GPU-hour estimate)
  2. Does the saved adapter have the same key layout as Kaggle's sample adapter?
  3. Do the bf16 and QAT checkpoints share architecture and chat template? (we train on bf16, serve on QAT)
Step 4 (does vLLM load it on the QAT model?) is a harness smoke run with this adapter in a variant folder.

Everything is written to /kaggle/working/: adapter/main_lora/, report.json.
"""

import glob
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

WORK = Path("/kaggle/working")
REPORT = {"stage": "start"}
T0 = time.time()

# Training settings for the tiny run. Train tasks only (harness/splits/train.txt), never dev.
TASK_IDS = ["fastapi_14099", "rich_3130", "requests_6644", "fastapi_14455"]
MAX_SEQ = 4096
STEPS = 8
RANK, ALPHA = 16, 32
LR = 1e-4
LOSS_CHUNK = 512


def log(msg):
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def save_report():
    REPORT["elapsed_s"] = round(time.time() - T0, 1)
    (WORK / "report.json").write_text(json.dumps(REPORT, indent=2, default=str))


def find_dir(pattern, what):
    hits = sorted(glob.glob(pattern, recursive=True))
    if not hits:
        raise SystemExit(f"{what} not found ({pattern})")
    return Path(hits[0]).parent


def main():
    # Offline install. L4x4 is only granted when the competition is attached, and then internet must be off, so
    # packages come from the competition wheelhouse (bitsandbytes, transformers 5.13) and our private dataset
    # bhoomikalnu/g5a-lora-wheels (transformers 5.23, peft, accelerate).
    log("pip install (offline)")
    links = []
    for pat in ("/kaggle/input/**/gemma-4-developer-agent-wheelhouse", "/kaggle/input/**/g5a-lora-wheels"):
        links += [p for p in glob.glob(pat, recursive=True) if os.path.isdir(p)]
    base = [sys.executable, "-m", "pip", "install", "-q", "--no-index"] + [f"--find-links={d}" for d in links]
    REPORT["wheel_dirs"] = links
    # Pin versions: the image's own transformers (5.0) predates Gemma 4 and would otherwise satisfy a bare requirement.
    res = subprocess.run(base + ["transformers==5.23.0", "peft==0.21.3", "accelerate==1.15.0", "bitsandbytes"],
                         capture_output=True, text=True)
    if res.returncode != 0:
        REPORT["pip_error"] = res.stderr[-3000:]
        save_report()
        raise SystemExit(f"offline pip install failed:\n{res.stderr[-3000:]}")

    import torch
    import transformers
    import peft
    from transformers import AutoConfig, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model

    REPORT["versions"] = {"torch": torch.__version__, "transformers": transformers.__version__, "peft": peft.__version__,
                          "python": sys.version.split()[0]}
    REPORT["gpus"] = [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]
    log(f"versions {REPORT['versions']} gpus {REPORT['gpus']}")

    bf16_dir = find_dir("/kaggle/input/**/gemma-4-31b-it/*/config.json", "bf16 Gemma 4 31B")
    qat_dir = find_dir("/kaggle/input/**/gemma-4-31b-it-qat-w4a16-ct/*/config.json", "QAT Gemma 4 31B")
    # Train-split tasks only (private dataset bhoomikalnu/g5a-lora-data). The competition itself can't be attached:
    # Kaggle rejects internet-enabled kernels that attach this competition, and we need internet for pip.
    tasks_path = Path(sorted(glob.glob("/kaggle/input/**/train_tasks.jsonl", recursive=True))[0])

    # 3. bf16 vs QAT: architecture and chat template.
    cb, cq = (json.loads((d / "config.json").read_text()) for d in (bf16_dir, qat_dir))
    REPORT["bf16_arch"], REPORT["qat_arch"] = cb.get("architectures"), cq.get("architectures")
    REPORT["qat_quantization"] = {k: cq.get("quantization_config", {}).get(k) for k in ("quant_method", "format", "ignore")}
    tb, tq = ((d / "chat_template.jinja").read_text() for d in (bf16_dir, qat_dir))
    REPORT["chat_template_identical"] = tb == tq
    REPORT["text_config_bf16"] = {k: cb.get("text_config", cb).get(k) for k in
                                  ("hidden_size", "num_hidden_layers", "num_attention_heads", "num_key_value_heads", "head_dim", "vocab_size")}
    REPORT["text_config_qat"] = {k: cq.get("text_config", cq).get(k) for k in REPORT["text_config_bf16"]}
    REPORT["stage"] = "configs"
    save_report()
    log(f"arch bf16={REPORT['bf16_arch']} qat={REPORT['qat_arch']} template_identical={REPORT['chat_template_identical']}")

    # Tokenizer + chat template from the QAT checkpoint: that is what vLLM serves at scoring time.
    tok = AutoTokenizer.from_pretrained(qat_dir)

    # 1. Load bf16 31B in 4-bit across the 4 L4s.
    arch = (cb.get("architectures") or ["AutoModelForCausalLM"])[0]
    model_cls = getattr(transformers, arch, None) or transformers.AutoModelForImageTextToText
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        llm_int8_skip_modules=["vision_tower", "multi_modal_projector", "embed_vision", "audio_tower", "embed_audio", "lm_head"],
    )
    n = torch.cuda.device_count()
    t = time.time()
    model = model_cls.from_pretrained(
        bf16_dir, quantization_config=bnb, torch_dtype=torch.bfloat16, device_map="auto",
        # lm_head is tied to the embeddings on GPU 0, so the 262K-vocab logits (and their fp32 grads) land there:
        # keep GPU 0 light and spread the layers over the other GPUs.
        max_memory={i: ("6GiB" if i == 0 else f"{int(torch.cuda.get_device_properties(i).total_memory / 1024**3 * 0.80)}GiB")
                    for i in range(n)},
        low_cpu_mem_usage=True,
    )
    REPORT["load_s"] = round(time.time() - t, 1)
    REPORT["model_class"] = type(model).__name__
    REPORT["devices_used"] = sorted({str(v) for v in getattr(model, "hf_device_map", {}).values()})
    REPORT["stage"] = "loaded"
    save_report()
    log(f"loaded {REPORT['model_class']} in {REPORT['load_s']}s on {REPORT['devices_used']}")

    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    lcfg = LoraConfig(
        r=RANK, lora_alpha=ALPHA, lora_dropout=0.0, bias="none", task_type="CAUSAL_LM",
        target_modules=r".*language_model\.layers\.\d+\.(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)",
    )
    model = get_peft_model(model, lcfg)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    REPORT["trainable_params"] = trainable
    log(f"trainable params {trainable:,}")

    # Tiny dataset: problem statement -> reference patch (assistant-only loss).
    tasks = {}
    for line in tasks_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            tasks[r["instance_id"]] = r
    examples = []
    for tid in TASK_IDS:
        r = tasks[tid]
        user = f"You are evaluating a software engineering task for repository {r['repo']}.\n\nProblem Statement:\n{r['problem_statement']}"
        msgs = [{"role": "user", "content": user}]
        # transformers 5 returns an Encoding from apply_chat_template(tokenize=True); render text, then tokenize.
        prompt_txt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
        full_txt = tok.apply_chat_template(msgs + [{"role": "assistant", "content": r["patch"]}], tokenize=False)
        prompt_ids = tok(prompt_txt, add_special_tokens=False)["input_ids"]
        full_ids = tok(full_txt, add_special_tokens=False)["input_ids"]
        full_ids = full_ids[:MAX_SEQ]
        labels = [-100] * min(len(prompt_ids), len(full_ids)) + full_ids[len(prompt_ids):]
        examples.append((full_ids, labels))
    REPORT["example_tokens"] = [len(e[0]) for e in examples]

    lm_head = model.get_output_embeddings()
    text_cfg = getattr(model.config, "text_config", model.config)
    cap = getattr(text_cfg, "final_logit_softcapping", None)
    REPORT["final_logit_softcapping"] = cap

    def head_logits(hc):
        lg = lm_head(hc).float()
        return torch.tanh(lg / cap) * cap if cap else lg

    def chunk_loss(hc, tc):
        return torch.nn.functional.cross_entropy(head_logits(hc.to(lm_head.weight.device)), tc, reduction="sum")

    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR)
    first_device = next(model.parameters()).device
    model.train()
    step_times, losses = [], []
    for step in range(STEPS):
        ids, labels = examples[step % len(examples)]
        t = time.time()
        # Only the assistant (patch) tokens carry loss. Full logits for ~4K tokens x 262K vocab (+fp32 copies and grads)
        # don't fit next to the weights, so take the final hidden states and compute the loss in checkpointed chunks:
        # only one chunk's logits exist at a time.
        start = next((i for i, l in enumerate(labels) if l != -100), len(labels) - 1)
        out = model(input_ids=torch.tensor([ids], device=first_device), logits_to_keep=1, output_hidden_states=True)
        h = out.hidden_states[-1][0]
        h_pred = h[start - 1:-1]
        target = torch.tensor(ids[start:], device=lm_head.weight.device)
        if step == 0:  # sanity check: our head reproduces the model's own last-position logits
            with torch.no_grad():
                REPORT["head_check_max_abs_diff"] = float((head_logits(h[-1:].to(lm_head.weight.device)) - out.logits[0, -1:].float().to(lm_head.weight.device)).abs().max())
        total = 0.0
        for c in range(0, len(target), LOSS_CHUNK):
            total = total + torch.utils.checkpoint.checkpoint(
                chunk_loss, h_pred[c:c + LOSS_CHUNK], target[c:c + LOSS_CHUNK], use_reentrant=False)
        loss = total / len(target)
        out.loss = loss
        loss.backward()
        opt.step()
        opt.zero_grad(set_to_none=True)
        torch.cuda.synchronize()
        step_times.append(round(time.time() - t, 2))
        losses.append(round(out.loss.item(), 4))
        log(f"step {step + 1}/{STEPS} tokens={len(ids)} loss={losses[-1]} {step_times[-1]}s")
    REPORT["step_times_s"], REPORT["losses"] = step_times, losses
    REPORT["tokens_per_s"] = round(sum(REPORT["example_tokens"][i % len(examples)] for i in range(STEPS)) / sum(step_times), 1)
    REPORT["peak_mem_gib"] = [round(torch.cuda.max_memory_allocated(i) / 1024**3, 1) for i in range(n)]
    REPORT["stage"] = "trained"
    save_report()

    # 2. Save in the harness layout and compare key names with Kaggle's sample adapter.
    out_dir = WORK / "adapter" / "main_lora"
    model.save_pretrained(out_dir, safe_serialization=True)
    cfg = json.loads((out_dir / "adapter_config.json").read_text())
    cfg["base_model_name_or_path"] = "google/gemma-4-31b-it-qat-w4a16-ct"
    cfg["inference_mode"] = True
    (out_dir / "adapter_config.json").write_text(json.dumps(cfg, indent=2))
    from safetensors import safe_open
    with safe_open(out_dir / "adapter_model.safetensors", "pt") as f:
        keys = sorted(f.keys())
    REPORT["adapter_files"] = {p.name: p.stat().st_size for p in out_dir.iterdir()}
    REPORT["adapter_n_tensors"] = len(keys)
    REPORT["adapter_key_examples"] = keys[:3] + keys[-2:]
    REPORT["keys_match_sample_layout"] = all(k.startswith("base_model.model.model.language_model.layers.") for k in keys)
    REPORT["stage"] = "done"
    save_report()
    log(f"saved adapter: {REPORT['adapter_files']} keys_match={REPORT['keys_match_sample_layout']}")


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        REPORT["error"] = f"{type(e).__name__}: {e}"
        REPORT["traceback"] = traceback.format_exc()[-4000:]
        save_report()
        raise
