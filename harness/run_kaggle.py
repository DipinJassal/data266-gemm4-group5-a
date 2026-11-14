"""Score a variant on a split using a Kaggle GPU notebook, launched from your laptop.

    python harness/run_kaggle.py baseline smoke
    python harness/run_kaggle.py variants/dipin-output-trim-v1 dev
    python harness/run_kaggle.py baseline smoke --max-tasks 2          # quick end-to-end check
    python harness/run_kaggle.py baseline smoke --task-ids rich_3180   # one task
    python harness/run_kaggle.py --fetch baseline smoke                # download results of the last run

What it does:
  1. Validates the variant offline (harness/validate.py). Stops on errors.
  2. Uploads baseline/, variants/, combined/ and harness/ as a PRIVATE Kaggle dataset `<you>/g5a-agents` (new version each time).
  3. Pushes a private GPU script kernel `<you>/g5a-eval-<variant>-<split>` that runs harness/kaggle_runner.py
     (internet off, competition data + wheelhouse + model attached).
  4. Waits for it to finish (unless --no-wait), downloads the outputs into
     harness/runs/<variant>/<split>/<UTC timestamp>/ and prints the summary (harness/summarize.py).

Uses your own Kaggle account and GPU quota (needs ~/.kaggle/access_token or kaggle.json, and the
competition rules accepted). L4 sessions use GPU quota at 2x the T4 rate; dev (30 tasks) at ~6 min/task is ~3 h.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
REPO = HARNESS.parent
sys.path.insert(0, str(HARNESS))
from validate import Checker  # noqa: E402

COMPETITION = "gemma-4-developer-agent"
WHEELHOUSE = "metric/gemma-4-developer-agent-wheelhouse"
DATASET_SLUG = "g5a-agents"
MODEL_SOURCE = "google/gemma-4/Other/{model}/2"
DEFAULT_MACHINE = "NvidiaL4"  # same as the official Getting Started notebook
# The wheelhouse is built for Python 3.12; Kaggle's latest image is 3.13. Use the official notebook's pinned image.
OFFICIAL_NOTEBOOK = "ryanholbrook/getting-started-gemma-4-developer-agent"
FALLBACK_DOCKER_IMAGE = "gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461"


def official_docker_image() -> str:
    """Docker image pinned by the official Getting Started notebook (falls back to the Nov 2026 value)."""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            kaggle("kernels", "pull", OFFICIAL_NOTEBOOK, "-m", "-p", tmp, timeout=120)
            image = json.loads((Path(tmp) / "kernel-metadata.json").read_text()).get("docker_image")
            if image:
                return image
    except Exception as e:  # network hiccup, CLI change, ...
        print(f"WARN  could not read the official notebook's docker image ({e}); using the fallback.")
    return FALLBACK_DOCKER_IMAGE
UPLOAD_DIRS = ("baseline", "variants", "combined", "harness")
UPLOAD_IGNORE = shutil.ignore_patterns("runs", "results", "__pycache__", "*.pyc", ".DS_Store", "*.zip")
DRY_RUN: Path | None = None  # set by --dry-run: write the dataset + kernel folders here instead of uploading


def keep_for_dry_run(src: Path, name: str) -> None:
    dest = DRY_RUN / name
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    print(f"[dry-run] wrote {dest}")


def kaggle(*args: str, check: bool = True, timeout: int | None = 600) -> str:
    # stdin closed + timeout: the CLI can stall on a network call long after Kaggle accepted the request.
    proc = subprocess.run(["kaggle", *args], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout)
    out = (proc.stdout + proc.stderr).strip()
    if check and proc.returncode != 0:
        raise SystemExit(f"kaggle {' '.join(args)} failed:\n{out}")
    return out


def kaggle_user() -> str:
    m = re.search(r"username:\s*(\S+)", kaggle("config", "view"))
    if not m or m.group(1) == "None":
        raise SystemExit("Kaggle username not found. Save your API token in ~/.kaggle/ first (see CLAUDE.md).")
    return m.group(1)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def variant_model(variant_dir: Path) -> str:
    c = Checker(variant_dir)
    root = c.find_root()
    cfg = c.load_yaml(root) if root else {}
    return str((cfg or {}).get("model", "gemma-4-31b-it-qat-w4a16-ct")).split("/")[-1]


def upload_repo(user: str, message: str) -> str:
    dataset = f"{user}/{DATASET_SLUG}"
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp)
        for d in UPLOAD_DIRS:
            if (REPO / d).is_dir():
                shutil.copytree(REPO / d, stage / d, ignore=UPLOAD_IGNORE)
        (stage / "G5A_REPO_MARKER").write_text("data266 group 5a repo snapshot\n")
        (stage / "dataset-metadata.json").write_text(json.dumps({
            "title": DATASET_SLUG, "id": dataset, "licenses": [{"name": "Apache 2.0"}],
        }))
        if DRY_RUN:
            keep_for_dry_run(stage, "dataset")
            return dataset
        # `datasets status` exits 0 only if the dataset exists (a missing one of your own returns 403).
        exists = subprocess.run(["kaggle", "datasets", "status", dataset], capture_output=True).returncode == 0
        if exists:
            print(f"Uploading new version of dataset {dataset} ...")
            kaggle("datasets", "version", "-p", str(stage), "-m", message, "-r", "tar", "-q")
        else:
            print(f"Creating private dataset {dataset} ...")
            kaggle("datasets", "create", "-p", str(stage), "-r", "tar", "-q")
    for _ in range(60):  # wait for Kaggle to process the upload
        status = kaggle("datasets", "status", dataset, check=False).lower()
        if "ready" in status:
            return dataset
        time.sleep(10)
    raise SystemExit(f"Dataset {dataset} not ready after 10 min (last status: {status})")


def push_kernel(user: str, kernel_slug: str, run_config: dict, model: str, dataset: str, machine: str, timeout: int | None) -> str:
    kernel_id = f"{user}/{kernel_slug}"
    runner = (HARNESS / "kaggle_runner.py").read_text()
    # repr(), not json.dumps(): the line is Python, so booleans must be True/False, not true/false.
    config_line = "RUN_CONFIG = " + repr(run_config)
    runner, n = re.subn(r"^RUN_CONFIG = .*$", lambda _: config_line, runner, count=1, flags=re.M)
    assert n == 1, "RUN_CONFIG line not found in kaggle_runner.py"
    with tempfile.TemporaryDirectory() as tmp:
        kdir = Path(tmp)
        (kdir / "kaggle_runner.py").write_text(runner)
        (kdir / "kernel-metadata.json").write_text(json.dumps({
            "id": kernel_id, "title": kernel_slug, "code_file": "kaggle_runner.py",
            "language": "python", "kernel_type": "script", "is_private": True,
            "enable_gpu": True, "enable_tpu": False, "enable_internet": False,
            "machine_shape": machine,
            "docker_image": official_docker_image(),
            "dataset_sources": [WHEELHOUSE, dataset],
            "competition_sources": [COMPETITION],
            "kernel_sources": [],
            "model_sources": [MODEL_SOURCE.format(model=model)],
        }, indent=2))
        if DRY_RUN:
            keep_for_dry_run(kdir, "kernel")
            return kernel_id
        args = ["kernels", "push", "-p", str(kdir), "--accelerator", machine]
        if timeout:
            args += ["-t", str(timeout)]
        try:
            print(kaggle(*args, timeout=600))
        except subprocess.TimeoutExpired:
            print("WARN  `kaggle kernels push` did not return in 10 min; the kernel is usually pushed anyway. Polling its status.")
    return kernel_id


def wait_for(kernel_id: str, poll: int = 60) -> str:
    print(f"Waiting for {kernel_id} (https://www.kaggle.com/code/{kernel_id}) ...")
    start = time.time()
    while True:
        status = kaggle("kernels", "status", kernel_id, check=False)
        low = status.lower()
        mins = (time.time() - start) / 60
        print(f"  {mins:5.1f} min  {status.splitlines()[-1] if status else '?'}", flush=True)
        if any(s in low for s in ("complete", "error", "cancel")):
            return low
        time.sleep(poll)


def fetch(kernel_id: str, variant: str, split: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = HARNESS / "runs" / slugify(variant) / split / stamp
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Downloading outputs to {dest.relative_to(REPO)} ...")
    kaggle("kernels", "output", kernel_id, "-p", str(dest), "-o")
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variant", help="folder relative to the repo root: baseline, variants/<name>, or combined")
    ap.add_argument("split", choices=["smoke", "dev", "train"], help="task split (train only for data collection)")
    ap.add_argument("--task-ids", nargs="+", default=[], help="run only these instance_ids (overrides the split list)")
    ap.add_argument("--max-tasks", type=int, default=0, help="run only the first N tasks of the split")
    ap.add_argument("--machine", default=DEFAULT_MACHINE, help=f"Kaggle accelerator (default {DEFAULT_MACHINE})")
    ap.add_argument("--timeout", type=int, help="kernel run-time limit in seconds")
    ap.add_argument("--no-wait", action="store_true", help="push and return; fetch later with --fetch")
    ap.add_argument("--fetch", action="store_true", help="only download + summarize the latest run of this kernel")
    ap.add_argument("--dry-run", action="store_true", help="build the dataset + kernel folders under harness/runs/_dryrun; upload nothing")
    args = ap.parse_args()
    global DRY_RUN
    if args.dry_run:
        DRY_RUN = HARNESS / "runs" / "_dryrun"
        DRY_RUN.mkdir(parents=True, exist_ok=True)

    # Kaggle is Linux: always pass posix paths in RUN_CONFIG (Windows \ breaks agent.yaml lookup).
    variant = args.variant.replace("\\", "/").strip("/")
    variant_dir = REPO / variant
    user = kaggle_user()
    kernel_slug = f"g5a-eval-{slugify(variant)}-{args.split}"[:50].strip("-")
    kernel_id = f"{user}/{kernel_slug}"

    if not args.fetch:
        if args.split == "dev" and (args.task_ids or args.max_tasks):
            print("NOTE: partial dev runs are fine for debugging, but log only full-dev scores.")
        c = Checker(variant_dir)
        c.run()
        for w in c.warnings:
            print(f"WARN  {w}")
        if c.errors:
            for e in c.errors:
                print(f"ERROR {e}")
            print("Fix the errors above (python harness/validate.py) before running on Kaggle.")
            return 1
        git_rev = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
        dirty = bool(subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True).stdout.strip())
        dataset = upload_repo(user, f"{variant} {args.split} @ {git_rev}{'+dirty' if dirty else ''}")
        run_config = {"variant": variant, "split": args.split, "task_ids": args.task_ids,
                      "max_tasks": args.max_tasks, "git_rev": git_rev, "dirty": dirty}
        push_kernel(user, kernel_slug, run_config, variant_model(variant_dir), dataset, args.machine, args.timeout)
        if DRY_RUN:
            print(f"[dry-run] would push kernel {kernel_id}; nothing uploaded.")
            return 0
        if args.no_wait:
            print(f"Pushed. Fetch later with: python harness/run_kaggle.py --fetch {variant} {args.split}")
            return 0
        status = wait_for(kernel_id)
        if "complete" not in status:
            print(f"Kernel ended with status: {status}. Downloading logs anyway.")

    dest = fetch(kernel_id, variant, args.split)
    results = next(dest.rglob("harness_results.jsonl"), None)
    if results is None:
        print(f"No harness_results.jsonl in the outputs. Check the kernel log in {dest} or on Kaggle.")
        return 1
    subprocess.run([sys.executable, str(HARNESS / "summarize.py"), str(results.parent)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
