"""V2 LoRA training (Bhoomika): LoRA on curated successful agent runs.

Runs INSIDE a Kaggle kernel with the competition attached (needed for L4 x4; internet off, packages offline).
Data: private dataset g5a-lora-v2-data, made by curate.py from fetched harness runs: v2_train.jsonl (resolved runs on
train-split tasks, smoke excluded, filtered by error-retry rate) and v2_heldout.jsonl (resolved smoke-task runs, for
held-out loss only). No dev task is ever read.

MODE = "dry"   -> CPU only: render + tokenize + mask every example, write stats and a masked preview. No model.
MODE = "train" -> QLoRA on bf16 Gemma 4 31B (4-bit NF4), held-out loss before/after, save the adapter in the
                  harness layout (adapters/main_lora/adapter_config.json + adapter_model.safetensors, bf16).

Loss is only on what the model itself generates at serving time: its thought (`<|channel>thought ... <channel|>`)
and tool call before each `<|tool_response>`, and the final thought + text + `<turn|>`. System prompt, task prompt
and tool responses are context only. Unlike V1, thoughts are part of the data, so the adapter keeps thinking.
"""

MODE = "dry"  # push_v2.py rewrites this line

import glob
import json
import math
import os
import random
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault("PYTORCH_ALLOC_CONF", "expandable_segments:True")
os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
WORK = Path("/kaggle/working")
T0 = time.time()
REPORT = {"mode": MODE, "stage": "start"}

SEED = 266
MAX_TOKENS = 10240          # longer examples are dropped (not truncated); 12288 ran out of memory on L4
RANK, ALPHA, DROPOUT = 16, 32, 0.0   # dropout off: it stores an extra activation copy per LoRA layer
LR, WARMUP, EPOCHS = 1e-4, 5, 2   # V3: 21 runs -> 57 pieces: 2 passes
LOSS_CHUNK = 512
MAX_TRAIN_MIN = 150         # stop training early rather than run past this many minutes
ENABLE_THINKING = True      # the served config has thinking_budget 4096 -> enable_thinking: true


def log(m):
    print(f"[{time.time() - T0:7.1f}s] {m}", flush=True)


def save_report():
    REPORT["elapsed_s"] = round(time.time() - T0, 1)
    (WORK / "v2_train_report.json").write_text(json.dumps(REPORT, indent=2, default=str))


def find_one(pattern):
    hits = sorted(glob.glob(pattern, recursive=True))
    if not hits:
        raise SystemExit(f"not found: {pattern}")
    return Path(hits[0])


def pip_install():
    links = [p for pat in ("/kaggle/input/**/gemma-4-developer-agent-wheelhouse", "/kaggle/input/**/g5a-lora-wheels")
             for p in glob.glob(pat, recursive=True) if os.path.isdir(p)]
    base = [sys.executable, "-m", "pip", "install", "-q", "--no-index"] + [f"--find-links={d}" for d in links]
    pkgs = ["transformers==5.23.0"] + (["peft==0.21.3", "accelerate==1.15.0", "bitsandbytes"] if MODE == "train" else [])
    r = subprocess.run(base + pkgs, capture_output=True, text=True)
    if r.returncode != 0:
        REPORT["pip_error"] = r.stderr[-3000:]
        save_report()
        raise SystemExit(f"offline pip install failed:\n{r.stderr[-3000:]}")


# ------------------------------------------------------------------------------------------- data
def prepare_messages(msgs):
    """Tool-call messages carry their thought as `reasoning` and no text; the final answer is its own message."""
    return [dict(m, content="") if m["role"] == "assistant" and m.get("tool_calls") else m for m in msgs]


SPAN_RE = re.compile(r"(?:<\|channel>thought\n(?:(?!<channel\|>).)*<channel\|>)?<\|tool_call>.*?<tool_call\|>(?:<\|tool_response>)?", re.S)


def target_char_spans(text, ex):
    """Character spans the model generates: thought + tool call (+ the token that ends it), and the final thought +
    text + <turn|>. A piece of a long run (curate.py) trains only on its window: calls [a, b) and maybe the final."""
    model_start = text.rfind("<|turn>model")
    if model_start < 0:
        raise ValueError("no model turn")
    spans = [(m.start(), m.end()) for m in SPAN_RE.finditer(text, model_start)]
    a, b = ex.get("loss_calls", [0, len(spans)])
    if len(spans) != len([m for m in ex["messages"] if m.get("tool_calls")]):
        raise ValueError(f"{ex['instance_id']}: {len(spans)} call spans, expected one per tool-call message")
    spans = spans[a:b]
    last_resp = text.rfind("<tool_response|>")
    end = text.find("<turn|>", last_resp)
    if ex.get("loss_final", True) and last_resp > model_start and end > 0:
        spans.append((last_resp + len("<tool_response|>"), end + len("<turn|>")))
    return spans


def encode(tok, ex):
    msgs = prepare_messages(ex["messages"])
    text = tok.apply_chat_template(msgs, tools=ex["tools"], tokenize=False, enable_thinking=ENABLE_THINKING)
    enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
    ids, offs = enc["input_ids"], enc["offset_mapping"]
    spans = target_char_spans(text, ex)
    labels = [-100] * len(ids)
    si = 0
    for i, (a, b) in enumerate(offs):
        while si < len(spans) and spans[si][1] <= a:
            si += 1
        if si < len(spans) and a >= spans[si][0] and b <= spans[si][1] and b > a:
            labels[i] = ids[i]
    return text, ids, labels


def load_split(name):
    p = find_one(f"/kaggle/input/**/v2_{name}.jsonl")
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


# ------------------------------------------------------------------------------------------- main
def main():
    pip_install()
    import transformers
    from transformers import AutoTokenizer

    qat_dir = find_one("/kaggle/input/**/gemma-4-31b-it-qat-w4a16-ct/*/tokenizer.json").parent
    tok = AutoTokenizer.from_pretrained(qat_dir)  # the served model's tokenizer + chat template

    data = {}
    for split in ("train", "heldout"):
        rows = []
        for ex in load_split(split):
            text, ids, labels = encode(tok, ex)
            n_t = sum(l != -100 for l in labels)
            rows.append({"id": f"{ex['instance_id']}#{ex.get('piece', '1/1')}", "ids": ids, "labels": labels,
                         "n": len(ids), "n_target": n_t, "text": text, "chars": ex.get("est_chars")})
        data[split] = rows
    REPORT["lengths"] = {s: [[x["id"], x["n"], x["n_target"], x["chars"]] for x in r] for s, r in data.items()}
    REPORT["tokenized"] = {s: {"n": len(r), "dropped_over_max": sum(x["n"] > MAX_TOKENS for x in r),
                               "zero_target": sum(x["n_target"] == 0 for x in r),
                               "tokens_kept": sum(x["n"] for x in r if x["n"] <= MAX_TOKENS),
                               "target_tokens_kept": sum(x["n_target"] for x in r if x["n"] <= MAX_TOKENS)} for s, r in data.items()}
    for s in data:
        data[s] = [x for x in data[s] if x["n"] <= MAX_TOKENS and x["n_target"] > 0]
    log(f"tokenized: {REPORT['tokenized']}")

    # masked preview of one example: target tokens wrapped in [[...]]
    ex = min(data["train"], key=lambda x: x["n"])
    pieces, cur, buf = [], None, []
    for t, l in zip(ex["ids"], ex["labels"]):
        on = l != -100
        if on != cur and buf:
            s = tok.decode(buf)
            pieces.append(f"[[{s}]]" if cur else s)
            buf = []
        cur = on
        buf.append(t)
    if buf:
        s = tok.decode(buf)
        pieces.append(f"[[{s}]]" if cur else s)
    (WORK / "masked_preview.txt").write_text("".join(pieces), encoding="utf-8")
    REPORT["preview_id"] = ex["id"]
    REPORT["stage"] = "tokenized"
    save_report()
    if MODE == "dry":
        log("dry run done")
        return

    import torch
    import peft
    from transformers import BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model

    REPORT["versions"] = {"torch": torch.__version__, "transformers": transformers.__version__, "peft": peft.__version__}
    bf16_dir = find_one("/kaggle/input/**/gemma-4-31b-it/*/config.json").parent
    cfg = json.loads((bf16_dir / "config.json").read_text())
    model_cls = getattr(transformers, cfg["architectures"][0])
    bnb = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=torch.bfloat16,
        llm_int8_skip_modules=["vision_tower", "multi_modal_projector", "embed_vision", "audio_tower", "embed_audio", "lm_head"])
    n = torch.cuda.device_count()
    t = time.time()
    # GPU 0 holds the tied embeddings/lm_head and the chunked logits; spread the layers evenly over GPUs 1..3
    model = model_cls.from_pretrained(bf16_dir, quantization_config=bnb, torch_dtype=torch.bfloat16, device_map="auto",
                                      max_memory={i: ("5GiB" if i == 0 else "7GiB") for i in range(n)}, low_cpu_mem_usage=True)
    REPORT["load_s"] = round(time.time() - t, 1)
    REPORT["devices_used"] = sorted({str(v) for v in getattr(model, "hf_device_map", {}).values()})
    log(f"loaded in {REPORT['load_s']}s on {REPORT['devices_used']}")

    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    model = get_peft_model(model, LoraConfig(
        r=RANK, lora_alpha=ALPHA, lora_dropout=DROPOUT, bias="none", task_type="CAUSAL_LM",
        target_modules=r".*language_model\.layers\.\d+\.(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)"))
    REPORT["trainable_params"] = sum(p.numel() for p in model.parameters() if p.requires_grad)

    lm_head = model.get_output_embeddings()
    cap = getattr(getattr(model.config, "text_config", model.config), "final_logit_softcapping", None)
    dev0 = next(model.parameters()).device

    def chunk_loss(hc, tc):
        lg = lm_head(hc.to(lm_head.weight.device)).float()
        if cap:
            lg = torch.tanh(lg / cap) * cap
        return torch.nn.functional.cross_entropy(lg, tc, reduction="sum")

    def example_loss(x):
        ids = x["ids"]
        pos = [i for i, l in enumerate(x["labels"]) if l != -100 and i > 0]
        out = model(input_ids=torch.tensor([ids], device=dev0), logits_to_keep=1, output_hidden_states=True)
        h = out.hidden_states[-1][0]
        pred = h[torch.tensor([p - 1 for p in pos], device=h.device)]
        tgt = torch.tensor([ids[p] for p in pos], device=lm_head.weight.device)
        total = 0.0
        for c in range(0, len(pos), LOSS_CHUNK):
            total = total + torch.utils.checkpoint.checkpoint(chunk_loss, pred[c:c + LOSS_CHUNK], tgt[c:c + LOSS_CHUNK], use_reentrant=False)
        return total, len(pos)

    def heldout_loss():
        model.eval()
        s = n_tok = 0
        with torch.no_grad():
            for x in data["heldout"]:
                try:
                    l, k = example_loss(x)
                except torch.OutOfMemoryError:
                    torch.cuda.empty_cache()
                    continue
                s += float(l); n_tok += k
        model.train()
        return round(s / max(n_tok, 1), 4)

    REPORT["heldout_loss_before"] = heldout_loss()
    log(f"held-out loss before: {REPORT['heldout_loss_before']}")
    save_report()

    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
    order = []
    rng = random.Random(SEED)
    for _ in range(EPOCHS):
        ep = list(range(len(data["train"])))
        rng.shuffle(ep)
        order += ep
    total_steps = len(order)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: min(1.0, (s + 1) / WARMUP) * 0.5 * (1 + math.cos(math.pi * min(s, total_steps) / total_steps)))
    model.train()
    losses, times = [], []
    t_train = time.time()
    for step, i in enumerate(order):
        x = data["train"][i]
        t = time.time()
        try:
            l, k = example_loss(x)
            (l / k).backward()
        except torch.OutOfMemoryError:
            # one example that does not fit must not kill the run: drop it and go on
            l = None
            opt.zero_grad(set_to_none=True)
            torch.cuda.empty_cache()
            REPORT.setdefault("oom_skipped", []).append(x["id"])
            sched.step()
            log(f"step {step + 1}/{total_steps} {x['id']} tokens={x['n']} OOM -> skipped")
            continue
        torch.nn.utils.clip_grad_norm_(params, 1.0)
        opt.step(); sched.step(); opt.zero_grad(set_to_none=True)
        losses.append(round(float(l) / k, 4)); times.append(round(time.time() - t, 1))
        log(f"step {step + 1}/{total_steps} {x['id']} tokens={x['n']} target={k} loss={losses[-1]} {times[-1]}s")
        if (time.time() - t_train) / 60 > MAX_TRAIN_MIN:
            REPORT["stopped_early_at_step"] = step + 1
            log("time guard: stopping early")
            break
        if (step + 1) % 10 == 0:
            REPORT["train_losses"], REPORT["step_times_s"] = losses, times
            save_report()
    REPORT["train_losses"], REPORT["step_times_s"] = losses, times
    REPORT["train_minutes"] = round((time.time() - t_train) / 60, 1)
    REPORT["peak_mem_gib"] = [round(torch.cuda.max_memory_allocated(i) / 1024**3, 1) for i in range(n)]
    REPORT["heldout_loss_after"] = heldout_loss()
    log(f"held-out loss after: {REPORT['heldout_loss_after']}")
    save_report()

    # save in the harness layout, bf16 weights, Kaggle-sample-style config with a plain target_modules list
    out_dir = WORK / "adapter" / "main_lora"
    model.save_pretrained(out_dir, safe_serialization=True)
    from safetensors.torch import load_file, save_file
    w = load_file(str(out_dir / "adapter_model.safetensors"))
    save_file({k: v.to(torch.bfloat16).contiguous() for k, v in w.items()}, str(out_dir / "adapter_model.safetensors"))
    cfg = {"alpha_pattern": {}, "auto_mapping": None, "base_model_name_or_path": "google/gemma-4-31b-it-qat-w4a16-ct",
           "bias": "none", "fan_in_fan_out": False, "inference_mode": True, "init_lora_weights": True,
           "layer_replication": None, "layers_pattern": None, "layers_to_transform": None, "loftq_config": {},
           "lora_alpha": ALPHA, "lora_dropout": 0.0, "megatron_config": None, "megatron_core": "megatron.core",
           "modules_to_save": None, "peft_type": "LORA", "r": RANK, "rank_pattern": {}, "revision": None,
           "target_modules": ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
           "task_type": "CAUSAL_LM", "use_dora": False, "use_rslora": False}
    (out_dir / "adapter_config.json").write_text(json.dumps(cfg, indent=2))
    for p in out_dir.iterdir():
        if p.name not in ("adapter_config.json", "adapter_model.safetensors"):
            p.unlink()
    REPORT["adapter_files"] = {p.name: p.stat().st_size for p in out_dir.iterdir()}
    REPORT["adapter_n_tensors"] = len(w)
    REPORT["stage"] = "done"
    save_report()
    log(f"saved adapter {REPORT['adapter_files']}")


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:
        REPORT["error"] = f"{type(e).__name__}: {e}"
        REPORT["traceback"] = traceback.format_exc()[-4000:]
        save_report()
        raise
