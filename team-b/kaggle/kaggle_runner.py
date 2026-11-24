"""Team B runner. Runs INSIDE a Kaggle GPU notebook (L4x4, internet off). Evaluates one Team B variant on one split.

Normally launched by `team-b/kaggle/run_kaggle.py` (Team B), which uploads the repo as a Kaggle dataset and writes
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


REQUIRED_CPYTHON = (3, 12)  # official wheelhouse ships cp312 tags
CP312_TAG = f"cp{REQUIRED_CPYTHON[0]}{REQUIRED_CPYTHON[1]}"
REQUIRED_GPU_COUNT = 4
REQUIRED_GPU_NAME = "L4"


def require_compatible_python() -> None:
    """Fail fast before pip if the kernel image is not CPython 3.12.x."""
    v = sys.version_info
    if (v.major, v.minor) != REQUIRED_CPYTHON:
        raise SystemExit(
            f"Incompatible Python {v.major}.{v.minor}.{v.micro} "
            f"({sys.executable}). The official dataset "
            f"metric/gemma-4-developer-agent-wheelhouse requires "
            f"CPython {REQUIRED_CPYTHON[0]}.{REQUIRED_CPYTHON[1]}.x "
            f"({CP312_TAG} wheels). "
            f"Pin a Python {REQUIRED_CPYTHON[0]}.{REQUIRED_CPYTHON[1]} "
            f"Kaggle docker_image (see team-b/kaggle/README.md / verified probe digest)."
        )
    log(f"Python OK: {v.major}.{v.minor}.{v.micro} (requires {REQUIRED_CPYTHON[0]}.{REQUIRED_CPYTHON[1]}.x)")


def count_l4_gpus(nvidia_smi_text: str | None) -> int:
    """Count NVIDIA L4 lines in `nvidia-smi -L` output."""
    if not nvidia_smi_text:
        return 0
    return sum(
        1
        for line in nvidia_smi_text.splitlines()
        if re.search(r"\bNVIDIA\s+L4\b", line, flags=re.I) or re.search(r"\bL4\b", line)
    )


def _probe_gpu() -> dict:
    """GPU visibility check before installing the wheelhouse (requires 4× L4)."""
    info = {
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "nvidia_smi": None,
        "l4_count": 0,
        "torch_cuda_available": None,
        "torch_gpu_count": None,
    }
    try:
        proc = subprocess.run(
            ["nvidia-smi", "-L"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        text = (proc.stdout or proc.stderr or "").strip() or f"exit={proc.returncode}"
        info["nvidia_smi"] = text
        info["l4_count"] = count_l4_gpus(text)
    except (OSError, subprocess.TimeoutExpired) as e:
        info["nvidia_smi"] = f"unavailable: {type(e).__name__}: {e}"
        info["l4_count"] = 0
    # torch may not be importable until after wheelhouse install; do not require it here.
    return info


def _probe_wheelhouse_tags(wheelhouse: Path) -> dict:
    """Confirm the attached wheelhouse still looks like official cp312 offline wheels."""
    wheels = sorted(wheelhouse.glob("*.whl"))
    sample = [w.name for w in wheels[:5]]
    cp312 = [w.name for w in wheels if CP312_TAG in w.name]
    py313 = [w.name for w in wheels if "cp313" in w.name]
    return {
        "wheel_count": len(wheels),
        "sample": sample,
        "cp312_count": len(cp312),
        "cp313_count": len(py313),
        "has_cp312": bool(cp312),
    }


def verify_mounted_upload_id(repo_dir: Path, cfg: dict) -> None:
    """Refuse to evaluate if the mounted g5b-agents dataset is a stale version.

    Port of harness PR #24 (G5A) to Team B's G5B_REPO_MARKER. Must run before
    wheel install, vLLM, or task evaluation.
    """
    want = cfg.get("upload_id")
    if not want:
        raise SystemExit(
            "BLOCKER: RUN_CONFIG is missing upload_id. Re-push with the current "
            "team-b/kaggle launcher (stale-dataset protection from PR #24)."
        )
    marker_path = repo_dir / "G5B_REPO_MARKER"
    if not marker_path.is_file():
        raise SystemExit(
            f"STALE UPLOAD: mounted repo dataset has no G5B_REPO_MARKER at {marker_path} "
            f"(expected upload_id={want})."
        )
    marker = marker_path.read_text()
    if f"upload_id={want}" not in marker:
        raise SystemExit(
            f"STALE UPLOAD: the mounted repo dataset is an older version "
            f"(marker: {marker.strip()!r}, expected upload_id={want}). "
            "Kaggle had not finished processing the new version; rerun the launcher."
        )
    log(f"repo dataset upload_id {want} verified")


def runtime_preflight(cfg: dict) -> dict:
    """Environment gates that must pass before installing the 41 competition wheels.

    Checks: CPython 3.12, wheelhouse cp312 tags, GPU probe, and selected docker_image
    recorded by the launcher (when present).
    """
    require_compatible_python()
    wheelhouse = find_one("**/gemma-4-developer-agent-wheelhouse", "the wheelhouse dataset")
    wheel_info = _probe_wheelhouse_tags(wheelhouse)
    if wheel_info["wheel_count"] == 0:
        raise SystemExit(f"Wheelhouse dataset at {wheelhouse} contains zero .whl files.")
    if not wheel_info["has_cp312"]:
        raise SystemExit(
            f"Wheelhouse at {wheelhouse} has no {CP312_TAG} wheels "
            f"(count={wheel_info['wheel_count']}, sample={wheel_info['sample']}). "
            "Refusing to pip-install an incompatible offline wheel set."
        )
    if (sys.version_info.major, sys.version_info.minor) != REQUIRED_CPYTHON and wheel_info["has_cp312"]:
        # require_compatible_python already exits; kept for clarity in logs.
        pass

    gpu_info = _probe_gpu()
    required_gpus = int(cfg.get("required_gpu_count") or REQUIRED_GPU_COUNT)
    required_gpu_name = str(cfg.get("required_gpu_name") or REQUIRED_GPU_NAME)
    l4_count = int(gpu_info.get("l4_count") or 0)
    if l4_count < required_gpus:
        raise SystemExit(
            f"Incompatible GPU topology: visible NVIDIA {required_gpu_name} count={l4_count}, "
            f"required={required_gpus}. nvidia-smi -L reported:\n{gpu_info.get('nvidia_smi')!r}\n"
            "Refuse to install the wheelhouse on a non-L4×4 runtime. "
            "Re-push with machine_shape/accelerator=NvidiaL4 and the probe-verified docker_image."
        )

    expected_image = cfg.get("docker_image")
    verification = cfg.get("image_verification")
    preflight = {
        "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "executable": sys.executable,
        "required_cpython": f"{REQUIRED_CPYTHON[0]}.{REQUIRED_CPYTHON[1]}",
        "docker_image_expected": expected_image,
        "image_verification": verification,
        "machine_shape_expected": cfg.get("machine_shape"),
        "required_gpu_count": required_gpus,
        "required_gpu_name": required_gpu_name,
        "wheelhouse": str(wheelhouse),
        "wheels": wheel_info,
        "gpu": gpu_info,
    }
    log(
        "PREFLIGHT OK: "
        f"python={preflight['python']} "
        f"wheels={wheel_info['wheel_count']} ({CP312_TAG}={wheel_info['cp312_count']}) "
        f"l4_count={l4_count}/{required_gpus} "
        f"docker_image_expected={expected_image!r} "
        f"image_verification={verification!r} "
        f"nvidia_smi={gpu_info['nvidia_smi']!r}"
    )
    if expected_image is None:
        log(
            "WARN  RUN_CONFIG has no docker_image; launcher should inject the pinned digest. "
            "Continuing after Python/wheel/GPU gates only."
        )
    return preflight


def install_wheelhouse() -> Path:
    """Install official competition wheels. Caller must run runtime_preflight() first."""
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
    return wheelhouse


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


def _jsonable(value):
    """One field of the result as JSON; never raises (a field that can't be serialized becomes a short note)."""
    try:
        if hasattr(value, "model_dump"):
            value = value.model_dump(mode="json")
        return json.loads(json.dumps(value, default=str))
    except Exception as e:
        return f"<not serializable: {type(value).__name__}: {type(e).__name__}: {str(e)[:200]}>"


def save_full_result(folder: Path, instance_id: str, result) -> None:
    """Dump every field of swegemma's result (incl. Phase 2 test output) for error analysis.

    Serialized field by field, so one field that pydantic can't dump (e.g. the SessionTrace) no longer loses the
    whole file. Trace fields are skipped: swegemma already writes them to swegemma/traces/.
    Ported from harness/kaggle_runner.py (8b967ed) for Team B's independent runner.
    """
    try:
        fields = getattr(type(result), "model_fields", None)
        if fields:
            raw = {name: getattr(result, name, None) for name in fields}
        elif hasattr(result, "__dict__"):
            raw = dict(vars(result))
        else:
            raw = {"repr": repr(result)}
        data = {}
        for name, value in raw.items():
            if "trace" in name.lower():
                data[name] = "<skipped: saved separately in swegemma/traces/>"
            else:
                data[name] = _jsonable(value)
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{instance_id}.json").write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:  # never let bookkeeping kill a run
        log(f"    (could not save full result for {instance_id}: {e})")


def main() -> None:
    cfg = RUN_CONFIG
    # Kaggle is Linux: normalize Windows paths that may appear in RUN_CONFIG.
    variant, split = cfg["variant"].replace("\\", "/").strip("/"), cfg["split"]
    started = datetime.now(timezone.utc)
    quiet_loggers()

    data_dir = find_one("**/gemma-4-developer-agent/tasks.jsonl", "the competition data").parent
    repo_dir = find_one("**/G5B_REPO_MARKER", "our repo dataset (uploaded by team-b/kaggle/run_kaggle.py)").parent
    # Fail before wheels / vLLM / tasks if Kaggle mounted an older g5b-agents version.
    verify_mounted_upload_id(repo_dir, cfg)

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

    # Fail before the ~41-wheel install if Python / wheel tags / GPU probe are wrong.
    preflight = runtime_preflight(cfg)
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
    preflight["gpu"]["torch_cuda_available"] = bool(torch.cuda.is_available())
    preflight["gpu"]["torch_gpu_count"] = gpu_count
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
        "docker_image": cfg.get("docker_image"),
        "image_verification": cfg.get("image_verification"),
        "preflight": preflight,
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
