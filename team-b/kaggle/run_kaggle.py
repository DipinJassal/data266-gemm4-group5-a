"""Team B Kaggle launcher — evaluate a Team B variant without touching Team A assets.

Examples (run from the repo root):

    python team-b/kaggle/run_kaggle.py team-b/variants/base smoke --dry-run
    python team-b/kaggle/run_kaggle.py team-b/variants/analyzer-plan smoke --max-tasks 2
    python team-b/kaggle/run_kaggle.py team-b/variants/diff-critic smoke
    python team-b/kaggle/run_kaggle.py --fetch team-b/variants/base smoke

What it does:
  1. Validates the selected Team B variant offline (harness/validate.py).
  2. Stages a PRIVATE Team B dataset `<you>/g5b-agents` containing ONLY:
       - G5B_REPO_MARKER
       - harness/ (shared splits + tooling; runs/ excluded)
       - the selected team-b/variants/<name>/ tree
     It does NOT upload Team A baseline/, variants/, or combined/.
  3. Pushes a private GPU script kernel `<you>/g5b-eval-...` that runs
     team-b/kaggle/kaggle_runner.py (internet off; competition + wheelhouse + model attached).
  4. Downloads outputs into team-b/kaggle/runs/<variant>/<split>/<UTC>/ and summarizes.

`--dry-run` never calls the Kaggle API, never needs credentials, and writes the staged
dataset + kernel under team-b/kaggle/runs/_dryrun/.

Requires ~/.kaggle credentials only for real uploads (not for --dry-run).
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

TB_KAGGLE = Path(__file__).resolve().parent
REPO = TB_KAGGLE.parents[1]  # .../data266-gemm4-group5-a
HARNESS = REPO / "harness"
sys.path.insert(0, str(HARNESS))
from validate import Checker  # noqa: E402  — shared offline validator (authorized Team B use)

COMPETITION = "gemma-4-developer-agent"
WHEELHOUSE = "metric/gemma-4-developer-agent-wheelhouse"
DATASET_SLUG = "g5b-agents"
KERNEL_PREFIX = "g5b-eval"
MODEL_SOURCE = "google/gemma-4/Other/{model}/2"
DEFAULT_MACHINE = "NvidiaL4"
OFFICIAL_NOTEBOOK = "ryanholbrook/getting-started-gemma-4-developer-agent"
FALLBACK_DOCKER_IMAGE = (
    "gcr.io/kaggle-private-byod/python@"
    "sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461"
)

# Only Team B variant trees + shared harness splits/tooling. Never Team A experiment folders.
# Ignore junk/outputs only. Do NOT ignore *.safetensors: restored adapter weights must
# ship inside the private Kaggle dataset (they stay out of git via the repo .gitignore).
UPLOAD_IGNORE = shutil.ignore_patterns(
    "runs", "results", "__pycache__", "*.pyc", ".DS_Store", "*.zip",
)
ALLOWED_VARIANT_PREFIX = "team-b/variants/"
DRY_RUN: Path | None = None


def die(msg: str, code: int = 1) -> None:
    raise SystemExit(msg) if code else SystemExit(code)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def kaggle(*args: str, check: bool = True, timeout: int | None = 600) -> str:
    proc = subprocess.run(
        ["kaggle", *args], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=timeout,
    )
    out = (proc.stdout + proc.stderr).strip()
    if check and proc.returncode != 0:
        die(f"kaggle {' '.join(args)} failed:\n{out}")
    return out


def kaggle_user() -> str:
    m = re.search(r"username:\s*(\S+)", kaggle("config", "view"))
    if not m or m.group(1) == "None":
        die("Kaggle username not found. Save your API token in ~/.kaggle/ first.")
    return m.group(1)


def official_docker_image(*, allow_network: bool) -> str:
    """Match the official Getting Started notebook image when possible."""
    if not allow_network:
        return FALLBACK_DOCKER_IMAGE
    try:
        with tempfile.TemporaryDirectory() as tmp:
            kaggle("kernels", "pull", OFFICIAL_NOTEBOOK, "-m", "-p", tmp, timeout=120)
            image = json.loads((Path(tmp) / "kernel-metadata.json").read_text()).get("docker_image")
            if image:
                return image
    except Exception as e:
        print(f"WARN  could not read official notebook docker image ({e}); using fallback.")
    return FALLBACK_DOCKER_IMAGE


def normalize_variant(raw: str) -> str:
    variant = raw.strip().strip("/")
    if not variant.startswith(ALLOWED_VARIANT_PREFIX):
        die(
            f"Team B launcher only accepts paths under {ALLOWED_VARIANT_PREFIX!r}. Got: {variant!r}\n"
            "Examples: team-b/variants/base | team-b/variants/analyzer-plan | team-b/variants/diff-critic"
        )
    if ".." in Path(variant).parts:
        die(f"Illegal variant path: {variant}")
    return variant


def variant_model(variant_dir: Path) -> str:
    c = Checker(variant_dir)
    root = c.find_root()
    cfg = c.load_yaml(root) if root else {}
    return str((cfg or {}).get("model", "gemma-4-31b-it-qat-w4a16-ct")).split("/")[-1]


def validate_variant(variant_dir: Path, *, strict: bool) -> tuple[list[str], list[str]]:
    c = Checker(variant_dir)
    c.run()
    return list(c.errors), list(c.warnings)


def only_adapter_weight_errors(errors: list[str]) -> bool:
    if not errors:
        return False
    return all("adapter_model.safetensors" in e for e in errors)


def structural_checks(variant: str, variant_dir: Path) -> list[str]:
    """Offline checks that do not require adapter weights or Kaggle credentials."""
    problems: list[str] = []
    if not variant_dir.is_dir():
        problems.append(f"variant directory missing: {variant_dir}")
        return problems
    if not (variant_dir / "agent.yaml").is_file():
        problems.append("agent.yaml missing at variant root")
    for rel in (
        "eval_config.yaml",
        "configs/sampling.yaml",
        "prompts/system.md",
        "adapters/main_lora/adapter_config.json",
        "adapters/tool_lora/adapter_config.json",
    ):
        if not (variant_dir / rel).is_file():
            problems.append(f"missing required relative file: {rel}")
    # Absolute / Team A path leakage in text configs
    for p in variant_dir.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in {".yaml", ".yml", ".md", ".json", ".txt"}:
            continue
        text = p.read_text(errors="ignore")
        if "/Users/" in text or "/home/" in text:
            problems.append(f"absolute local path in {p.relative_to(variant_dir)}")
        if "cursor" in text.lower() and "agent" in str(p):
            # soft: only flag obvious Cursor deps in agent yaml
            pass
    if not (HARNESS / "splits" / "smoke.txt").is_file():
        problems.append("shared harness/splits/smoke.txt missing (needed at runtime)")
    if not (TB_KAGGLE / "kaggle_runner.py").is_file():
        problems.append("team-b/kaggle/kaggle_runner.py missing")
    # Secrets must not live in the variant tree
    for bad in variant_dir.rglob("*"):
        if bad.name in {"kaggle.json", ".env"} or bad.suffix in {".pem", ".key"}:
            problems.append(f"secret-like file in variant: {bad.relative_to(variant_dir)}")
    return problems


def stage_dataset(variant: str, variant_dir: Path, stage: Path) -> None:
    """Build the private Team B dataset contents under stage/."""
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)

    # Shared splits/tooling only (authorized Team B use of shared harness).
    harness_dest = stage / "harness"
    shutil.copytree(
        HARNESS,
        harness_dest,
        ignore=UPLOAD_IGNORE,
    )
    # Drop Team A run artifacts if any slipped through
    for extra in ("runs",):
        p = harness_dest / extra
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)

    # Selected Team B variant only — preserve relative path team-b/variants/<name>
    dest_variant = stage / variant
    dest_variant.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(variant_dir, dest_variant, ignore=UPLOAD_IGNORE)

    # Never stage Team A experiment trees
    for forbidden in ("baseline", "variants", "combined", "lora", "docs"):
        if (stage / forbidden).exists():
            die(f"Refusing to stage Team A path {forbidden}/ in Team B dataset")

    (stage / "G5B_REPO_MARKER").write_text(
        "data266 group 5 team-b private evaluation snapshot\n"
        f"variant={variant}\n"
        "do-not-upload-team-a-variants\n"
    )


def write_dataset_metadata(stage: Path, dataset: str) -> None:
    (stage / "dataset-metadata.json").write_text(json.dumps({
        "title": DATASET_SLUG,
        "id": dataset,
        "licenses": [{"name": "Apache 2.0"}],
    }, indent=2))


def keep_dry_run(src: Path, name: str) -> Path:
    assert DRY_RUN is not None
    dest = DRY_RUN / name
    shutil.rmtree(dest, ignore_errors=True)
    shutil.copytree(src, dest)
    print(f"[dry-run] wrote {dest.relative_to(REPO)}")
    return dest


def upload_dataset(user: str, variant: str, variant_dir: Path, message: str) -> str:
    dataset = f"{user}/{DATASET_SLUG}"
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "dataset"
        stage_dataset(variant, variant_dir, stage)
        write_dataset_metadata(stage, dataset)
        if DRY_RUN:
            keep_dry_run(stage, "dataset")
            return dataset
        exists = subprocess.run(["kaggle", "datasets", "status", dataset], capture_output=True).returncode == 0
        if exists:
            print(f"Uploading new version of private Team B dataset {dataset} ...")
            kaggle("datasets", "version", "-p", str(stage), "-m", message, "-r", "tar", "-q")
        else:
            print(f"Creating private Team B dataset {dataset} ...")
            kaggle("datasets", "create", "-p", str(stage), "-r", "tar", "-q")
    for _ in range(60):
        status = kaggle("datasets", "status", dataset, check=False).lower()
        if "ready" in status:
            return dataset
        time.sleep(10)
    die(f"Dataset {dataset} not ready after 10 min (last status: {status})")


def push_kernel(
    user: str,
    kernel_slug: str,
    run_config: dict,
    model: str,
    dataset: str,
    machine: str,
    timeout: int | None,
    *,
    allow_network: bool,
) -> str:
    kernel_id = f"{user}/{kernel_slug}"
    runner = (TB_KAGGLE / "kaggle_runner.py").read_text()
    config_line = "RUN_CONFIG = " + repr(run_config)
    runner, n = re.subn(r"^RUN_CONFIG = .*$", lambda _: config_line, runner, count=1, flags=re.M)
    if n != 1:
        die("RUN_CONFIG line not found in team-b/kaggle/kaggle_runner.py")
    with tempfile.TemporaryDirectory() as tmp:
        kdir = Path(tmp)
        (kdir / "kaggle_runner.py").write_text(runner)
        (kdir / "kernel-metadata.json").write_text(json.dumps({
            "id": kernel_id,
            "title": kernel_slug,
            "code_file": "kaggle_runner.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": True,
            "enable_tpu": False,
            "enable_internet": False,
            "machine_shape": machine,
            "docker_image": official_docker_image(allow_network=allow_network),
            "dataset_sources": [WHEELHOUSE, dataset],
            "competition_sources": [COMPETITION],
            "kernel_sources": [],
            "model_sources": [MODEL_SOURCE.format(model=model)],
        }, indent=2))
        if DRY_RUN:
            keep_dry_run(kdir, "kernel")
            return kernel_id
        args = ["kernels", "push", "-p", str(kdir), "--accelerator", machine]
        if timeout:
            args += ["-t", str(timeout)]
        try:
            print(kaggle(*args, timeout=600))
        except subprocess.TimeoutExpired:
            print("WARN  `kaggle kernels push` timed out; kernel may still be queued. Polling status.")
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
    dest = TB_KAGGLE / "runs" / slugify(variant) / split / stamp
    dest.mkdir(parents=True, exist_ok=True)
    print(f"Downloading outputs to {dest.relative_to(REPO)} ...")
    kaggle("kernels", "output", kernel_id, "-p", str(dest), "-o")
    return dest


def inspect_dry_run_stage(variant: str, model: str, user_placeholder: str, dataset: str, kernel_id: str) -> None:
    assert DRY_RUN is not None
    ds = DRY_RUN / "dataset"
    kn = DRY_RUN / "kernel"
    print("\n=== Team B dry-run inspection ===")
    print(f"dataset_slug: {dataset}")
    print(f"kernel_id:    {kernel_id}")
    print(f"model:        {model}")
    print(f"variant:      {variant}")
    marker = ds / "G5B_REPO_MARKER"
    print(f"G5B_REPO_MARKER: {'PASS' if marker.is_file() else 'FAIL'}")
    print(f"variant staged: {'PASS' if (ds / variant / 'agent.yaml').is_file() else 'FAIL'}")
    print(f"harness/splits: {'PASS' if (ds / 'harness' / 'splits' / 'smoke.txt').is_file() else 'FAIL'}")
    for bad in ("baseline", "variants", "combined", "lora"):
        present = (ds / bad).exists()
        print(f"Team A path {bad}/ absent: {'PASS' if not present else 'FAIL'}")
    meta = json.loads((kn / "kernel-metadata.json").read_text())
    print(f"kernel private: {'PASS' if meta.get('is_private') else 'FAIL'}")
    print(f"internet off:   {'PASS' if not meta.get('enable_internet') else 'FAIL'}")
    print(f"competition:    {meta.get('competition_sources')}")
    print(f"datasets:       {meta.get('dataset_sources')}")
    print(f"models:         {meta.get('model_sources')}")
    runner = (kn / "kaggle_runner.py").read_text()
    print(f"runner uses G5B marker: {'PASS' if 'G5B_REPO_MARKER' in runner else 'FAIL'}")
    print(f"runner avoids G5A marker: {'PASS' if 'G5A_REPO_MARKER' not in runner else 'FAIL'}")
    # No credentials staged
    secret_hits = [p for p in ds.rglob("*") if p.name in {"kaggle.json", ".env"}]
    print(f"no secrets in stage: {'PASS' if not secret_hits else 'FAIL ' + str(secret_hits)}")
    weight_hits = list(ds.rglob("*.safetensors"))
    if weight_hits:
        print(f"adapter weights in stage: PRESENT ({len(weight_hits)} files) — OK for private upload, never commit")
    else:
        print("adapter weights in stage: MISSING — restore before real Kaggle runs; structural dry-run still OK")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variant", help="Team B variant path, e.g. team-b/variants/base")
    ap.add_argument("split", choices=["smoke", "dev", "train"], help="task split")
    ap.add_argument("--task-ids", nargs="+", default=[], help="run only these instance_ids")
    ap.add_argument("--max-tasks", type=int, default=0, help="first N tasks of the split")
    ap.add_argument("--machine", default=DEFAULT_MACHINE, help=f"Kaggle accelerator (default {DEFAULT_MACHINE})")
    ap.add_argument("--timeout", type=int, help="kernel run-time limit in seconds")
    ap.add_argument("--no-wait", action="store_true", help="push and return; fetch later with --fetch")
    ap.add_argument("--fetch", action="store_true", help="download + summarize the latest run of this kernel")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="stage dataset+kernel under team-b/kaggle/runs/_dryrun; no Kaggle API, no credentials",
    )
    ap.add_argument(
        "--require-adapters",
        action="store_true",
        help="fail if validate.py reports missing adapter_model.safetensors (default: warn and continue for dry-run)",
    )
    args = ap.parse_args()

    global DRY_RUN
    variant = normalize_variant(args.variant)
    variant_dir = REPO / variant
    kernel_slug = f"{KERNEL_PREFIX}-{slugify(variant)}-{args.split}"[:50].strip("-")

    if args.dry_run:
        DRY_RUN = TB_KAGGLE / "runs" / "_dryrun"
        DRY_RUN.mkdir(parents=True, exist_ok=True)
        user = "dry-run-user"
        allow_network = False
    else:
        user = kaggle_user()
        allow_network = True

    kernel_id = f"{user}/{kernel_slug}"

    if not args.fetch:
        if args.split == "dev" and (args.task_ids or args.max_tasks):
            print("NOTE: partial dev runs are fine for debugging; log only full-dev scores for selection.")

        struct_problems = structural_checks(variant, variant_dir)
        if struct_problems:
            for p in struct_problems:
                print(f"STRUCT ERROR  {p}")
            print("Fix structural problems before running.")
            return 1
        print("STRUCT CHECKS: PASS")

        errors, warnings = validate_variant(variant_dir, strict=args.require_adapters)
        for w in warnings:
            print(f"WARN  {w}")
        if errors:
            for e in errors:
                print(f"ERROR {e}")
            if only_adapter_weight_errors(errors) and not args.require_adapters:
                print(
                    "VALIDATE: BLOCKED (missing adapter_model.safetensors). "
                    "Structural packaging can still be dry-run staged; restore weights before real Kaggle runs."
                )
            else:
                print("Fix validation errors (python harness/validate.py <variant>) before continuing.")
                return 1
        else:
            print("VALIDATE: PASS")

        git_rev = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(["git", "-C", str(REPO), "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
        )
        model = variant_model(variant_dir) if (variant_dir / "agent.yaml").is_file() else "gemma-4-31b-it-qat-w4a16-ct"
        dataset = upload_dataset(user, variant, variant_dir, f"{variant} {args.split} @ {git_rev}{'+dirty' if dirty else ''}")
        run_config = {
            "variant": variant,
            "split": args.split,
            "task_ids": args.task_ids,
            "max_tasks": args.max_tasks,
            "git_rev": git_rev,
            "dirty": dirty,
            "team": "B",
        }
        push_kernel(
            user, kernel_slug, run_config, model, dataset, args.machine, args.timeout, allow_network=allow_network,
        )
        if DRY_RUN:
            inspect_dry_run_stage(variant, model, user, dataset, kernel_id)
            print(f"[dry-run] would push kernel {kernel_id}; nothing uploaded; no credentials used.")
            return 0
        if args.no_wait:
            print(f"Pushed. Fetch later with: python team-b/kaggle/run_kaggle.py --fetch {variant} {args.split}")
            return 0
        status = wait_for(kernel_id)
        if "complete" not in status:
            print(f"Kernel ended with status: {status}. Downloading logs anyway.")

    dest = fetch(kernel_id, variant, args.split)
    results = next(dest.rglob("harness_results.jsonl"), None)
    if results is None:
        print(f"No harness_results.jsonl in the outputs. Check {dest} or the Kaggle kernel log.")
        return 1
    subprocess.run([sys.executable, str(HARNESS / "summarize.py"), str(results.parent)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
