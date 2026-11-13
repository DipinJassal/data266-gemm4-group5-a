"""Runs INSIDE a Kaggle GPU notebook (L4x4, internet off). Evaluates one variant on one split.

Normally launched by `harness/run_kaggle.py`, which uploads the repo as a Kaggle dataset and writes
RUN_CONFIG below. You can also paste this file into a Kaggle notebook by hand: attach the competition,
the `metric/gemma-4-developer-agent-wheelhouse` dataset, the Gemma 4 31B model and our repo dataset,
then edit RUN_CONFIG.

Mirrors the official "Getting Started" notebook (ryanholbrook/getting-started-gemma-4-developer-agent):
wheelhouse install -> vLLM server -> swegemma Evaluator (Phase 1 agent + Phase 2 verification).

Outputs (in /kaggle/working/results/<variant>/<split>/):
  harness_results.jsonl   one line per task: instance_id, repo, resolved, duration_seconds, tool_calls, ...
  run_info.json           variant, split, budgets, GPU count, start/end time
  submission.csv          id,prediction (same shape Kaggle scores)
  + swegemma's own artifacts (patches/, logs/, traces/, test_outputs/) when it writes them
"""

# RUN_CONFIG (run_kaggle.py rewrites this line)
RUN_CONFIG = {"variant": "baseline", "split": "smoke", "task_ids": [], "max_tasks": 0}

import asyncio
import concurrent.futures
import glob
import importlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

for k, v in {
    "TRANSFORMERS_NO_TF": "1", "TRANSFORMERS_NO_FLAX": "1", "TRANSFORMERS_OFFLINE": "1",
    "VLLM_NO_USAGE_STATS": "1", "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
    "VLLM_ENGINE_READY_TIMEOUT_S": "1200", "VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS": "1",
    "NCCL_DEBUG": "WARN", "LITELLM_LOCAL_MODEL_COST_MAP": "True", "LITELLM_TELEMETRY": "False",
    "LITELLM_LOG": "WARNING", "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True",
    "OTEL_SDK_DISABLED": "true", "OTEL_PYTHON_DISABLED": "true",
}.items():
    os.environ[k] = v
os.environ.setdefault("OPENAI_API_KEY", "EMPTY")
os.environ.setdefault("LOCAL_API_KEY", "EMPTY")

INPUT = Path("/kaggle/input")
WORKING = Path("/kaggle/working")
ALLOWED_MODEL_NAMES = {
    "gemma-4-31b-it-qat-w4a16-ct", "gemma-4-12b-it-qat-w4a16-ct",
    "gemma-4-e4b-it-qat-w4a16-ct", "gemma-4-e2b-it-qat-w4a16-ct",
}
MODEL_VLLM_EXTRA_ARGS = {
    "gemma-4-12b-it-qat-w4a16-ct": ("--hf-overrides", '{"architectures": ["Gemma4ForCausalLM"], "model_type": "gemma4"}'),
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def quiet_loggers() -> None:
    for name in ("LiteLLM", "LiteLLM Router", "LiteLLM Proxy", "litellm", "httpx", "httpcore",
                 "openai", "urllib3", "opentelemetry", "opentelemetry.context"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.WARNING)
        if "litellm" in name.lower():
            lg.propagate = False
            lg.handlers.clear()


def find_one(pattern: str, what: str) -> Path:
    hits = sorted(INPUT.glob(pattern))
    if not hits:
        raise SystemExit(f"Could not find {what} under /kaggle/input (pattern {pattern!r}). Is the input attached?")
    return hits[0]


def install_wheelhouse() -> None:
    wheelhouse = find_one("**/gemma-4-developer-agent-wheelhouse", "the wheelhouse dataset")
    for pattern in ("/usr/local/lib/python*/dist-packages/*cutlass*.pth", "/usr/local/lib/python*/site-packages/*cutlass*.pth"):
        for pth in glob.glob(pattern):
            try:
                os.unlink(pth)
            except OSError:
                pass
    tmp = Path("/tmp/wheelhouse")
    tmp.mkdir(parents=True, exist_ok=True)
    for w in wheelhouse.glob("*.whl"):
        if "cutlass" in w.name.lower():
            continue
        name = w.name.replace("cu128", "+cu128") if ("cu128" in w.name and "+" not in w.name) else w.name
        target = tmp / name
        if not target.exists():
            try:
                os.symlink(w, target)
            except OSError:
                shutil.copyfile(w, target)
    wheels = sorted(str(w) for w in tmp.glob("*.whl"))
    log(f"Installing {len(wheels)} wheels from {wheelhouse} ...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--no-deps", "--force-reinstall", *wheels], check=True)
    importlib.invalidate_caches()
    quiet_loggers()


def run_sync(fn, *args, **kwargs):
    """Run an async function to completion, also when an event loop is already running (notebooks)."""
    def go():
        return asyncio.run(fn(*args, **kwargs))
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(go).result()
    return go()


def result_record(task, result, wall_seconds: float) -> dict:
    patch = (getattr(result, "agent_patch", None) or "").strip()
    rec = {
        "instance_id": task.instance_id,
        "repo": task.repo,
        "resolved": bool(getattr(result, "resolved", False)),
        "duration_seconds": getattr(result, "duration_seconds", None),
        "wall_seconds": round(wall_seconds, 1),
        "tool_calls": getattr(result, "tool_calls", None),
        "test_exit_code": getattr(result, "test_exit_code", None),
        "patch_chars": len(patch),
        "error": getattr(result, "error", None) or getattr(result, "agent_error", None),
    }
    for extra in ("turns", "total_tokens", "input_tokens", "output_tokens", "patch_submitted", "termination_reason"):
        if hasattr(result, extra):
            rec[extra] = getattr(result, extra)
    return json.loads(json.dumps(rec, default=str))


def save_full_result(folder: Path, instance_id: str, result) -> None:
    """Dump every field of swegemma's result (incl. Phase 2 test output) for error analysis."""
    try:
        if hasattr(result, "model_dump"):
            data = result.model_dump(mode="json")
        elif hasattr(result, "__dict__"):
            data = dict(vars(result))
        else:
            data = {"repr": repr(result)}
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{instance_id}.json").write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:  # never let bookkeeping kill a run
        log(f"    (could not save full result for {instance_id}: {e})")


def main() -> None:
    cfg = RUN_CONFIG
    variant, split = cfg["variant"], cfg["split"]
    started = datetime.now(timezone.utc)
    quiet_loggers()

    data_dir = find_one("**/gemma-4-developer-agent/tasks.jsonl", "the competition data").parent
    repo_dir = find_one("**/G5A_REPO_MARKER", "our repo dataset (uploaded by run_kaggle.py)").parent

    # 1. Copy the variant to a writable folder.
    src = repo_dir / variant
    if not (src / "agent.yaml").is_file() and not any((src / n).is_file() for n in ("agent.yml", "root_agent.yaml", "root_agent.yml")):
        raise SystemExit(f"No agent.yaml in {src}")
    agent_dir = WORKING / "agent"
    shutil.rmtree(agent_dir, ignore_errors=True)
    shutil.copytree(src, agent_dir)

    # 2. Pick the tasks.
    if cfg.get("task_ids"):
        wanted = list(cfg["task_ids"])
    else:
        wanted = [l.strip() for l in (repo_dir / "harness" / "splits" / f"{split}.txt").read_text().splitlines() if l.strip()]
    if cfg.get("max_tasks"):
        wanted = wanted[: int(cfg["max_tasks"])]

    install_wheelhouse()

    import litellm
    import torch
    import yaml
    from adk_submission import VllmConfig, VllmServer, discover_adapters, validate_directory
    from adk_submission.discovery import discover_declared_models
    from google.adk.agents.context_cache_config import ContextCacheConfig
    from google.adk.apps._configs import EventsCompactionConfig
    from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, EvalConfig, build_submission_limits
    from swegemma.evaluate import Evaluator
    from swegemma.models import load_tasks

    litellm.drop_params = True
    limits, gen_constraints = build_submission_limits()
    validate_directory(agent_dir, limits=limits)  # official compiler-side validation

    tasks_by_id = {t.instance_id: t for t in load_tasks(data_dir / "tasks.jsonl")}
    missing = [i for i in wanted if i not in tasks_by_id]
    if missing:
        raise SystemExit(f"Unknown task ids: {missing}")
    tasks = [tasks_by_id[i] for i in wanted]

    # 3. Budgets from the variant's eval_config.yaml (same defaults as the official notebook).
    ev_file = next((p for n in ("eval_config.yaml", "eval_config.yml") if (p := agent_dir / n).is_file()), None)
    raw = (yaml.safe_load(ev_file.read_text()) or {}) if ev_file else {}
    ev = raw.get("evaluation", raw)
    budgets = {
        "timeout_seconds": int(ev.get("timeout_seconds", 300)),
        "verification_timeout_seconds": int(ev.get("verification_timeout_seconds", 300)),
        "max_tool_calls": int(ev.get("max_tool_calls", 100)),
        "max_time_minutes": float(ev.get("max_time_minutes", 60.0)),
        "max_turns": int(t) if (t := ev.get("max_turns", ev.get("max_llm_calls"))) is not None else None,
    }

    # 4. Start vLLM with the declared model and any adapters.
    models_declared = discover_declared_models(agent_dir)
    assert len(models_declared) == 1, f"Expected exactly 1 declared model, got {sorted(models_declared)}"
    model_name = next(iter(models_declared))
    assert model_name in ALLOWED_MODEL_NAMES, f"Model {model_name!r} not allowed"
    model_path = find_one(f"**/{model_name}/*/config.json", f"model weights for {model_name}").parent

    adapters = discover_adapters(str(agent_dir), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    adapter_map = getattr(adapters, "adapters", None) or {}
    ranks = [r for info in adapter_map.values() if (r := getattr(info, "rank", None)) is not None and r > 0]
    gpu_count = torch.cuda.device_count() if torch.cuda.is_available() else 0
    if gpu_count < 4:
        log(f"WARNING: {gpu_count} GPU(s) visible; Kaggle scoring uses 4x L4. Timings will not be representative.")
    tp = 4 if gpu_count >= 4 else (2 if gpu_count >= 2 else 1)

    server = VllmServer(
        VllmConfig(
            model=str(model_path), port=8000, host="127.0.0.1",
            tool_call_parser="gemma4", reasoning_parser="gemma4", max_model_len=32768,
            dtype="bfloat16" if (torch.cuda.is_available() and torch.cuda.is_bf16_supported()) else "auto",
            gpu_memory_utilization=0.90, enable_auto_tool_choice=True,
            enable_lora=bool(adapter_map), max_loras=max(1, len(adapter_map)),
            max_lora_rank=max(ranks) if ranks else 128, scheduler_reserve_full_isl=False,
            tensor_parallel_size=tp, startup_timeout=60 * 20,
            extra_args=MODEL_VLLM_EXTRA_ARGS.get(model_name, ()),
        ),
        adapter_manifest=adapters,
    )
    t0 = time.time()
    server.start()
    vllm_start_seconds = round(time.time() - t0, 1)
    log(f"vLLM up in {vllm_start_seconds}s (model={model_name}, tp={tp}, adapters={sorted(adapter_map)})")
    models = server.create_model_registry(aliases=[model_name], model_prefix="openai/", api_key=os.environ["LOCAL_API_KEY"])

    # 5. Evaluate.
    out_dir = WORKING / "results" / variant.replace("/", "__") / split
    out_dir.mkdir(parents=True, exist_ok=True)
    eval_config = EvalConfig(
        tasks_path=data_dir / "tasks.jsonl",
        snapshots_dir=data_dir / "snapshots",
        results_dir=out_dir / "swegemma",
        submission_dir=agent_dir,
        models=models,
        sandbox="subprocess",
        limits=limits,
        generation_constraints=gen_constraints,
        adapter_manifest=adapters,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(
            compaction_interval=15, overlap_size=2, token_threshold=14336, event_retention_size=5,
        ),
        graph_dir=str(data_dir / "graphs"),
        embeddings_dir=str(data_dir / "embeddings"),
        wheels_dir=data_dir / "wheels",
        verbose=False,
        **budgets,
    )
    evaluator = Evaluator(eval_config)

    run_info = {
        "variant": variant, "split": split, "n_tasks": len(tasks), "model": model_name,
        "git_rev": cfg.get("git_rev"), "dirty": cfg.get("dirty"),
        "adapters": sorted(adapter_map), "gpu_count": gpu_count, "budgets": budgets,
        "vllm_start_seconds": vllm_start_seconds, "started_utc": started.isoformat(),
    }
    (out_dir / "run_info.json").write_text(json.dumps(run_info, indent=2))

    results_path = out_dir / "harness_results.jsonl"
    predictions = []
    resolved = 0
    with results_path.open("w") as fh:
        for idx, task in enumerate(tasks, start=1):
            log(f"[{idx}/{len(tasks)}] {task.instance_id} ({task.repo})")
            t_task = time.time()
            try:
                result = run_sync(evaluator.evaluate_task, task=task, task_index=idx, total_tasks=len(tasks))
                rec = result_record(task, result, time.time() - t_task)
                patch = (getattr(result, "agent_patch", None) or "").strip()
                save_full_result(out_dir / "task_details", task.instance_id, result)
            except Exception as e:  # keep going: one crashed task must not kill the run
                rec = {"instance_id": task.instance_id, "repo": task.repo, "resolved": False,
                       "wall_seconds": round(time.time() - t_task, 1), "error": f"HARNESS_CRASH: {type(e).__name__}: {e}"}
                patch = ""
            resolved += rec["resolved"]
            fh.write(json.dumps(rec) + "\n")
            fh.flush()
            predictions.append((task.instance_id, patch or "NO_PATCH"))
            log(f"    resolved={rec['resolved']} wall={rec['wall_seconds']}s tool_calls={rec.get('tool_calls')} "
                f"patch_chars={rec.get('patch_chars', 0)} | running {resolved}/{idx}")

    import csv
    with (out_dir / "submission.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "prediction"])
        w.writerows(predictions)

    run_info.update({"finished_utc": datetime.now(timezone.utc).isoformat(), "resolved": resolved})
    (out_dir / "run_info.json").write_text(json.dumps(run_info, indent=2))
    log(f"DONE {variant} on {split}: {resolved}/{len(tasks)} resolved -> {out_dir}")
    server.stop()


if __name__ == "__main__":
    main()
