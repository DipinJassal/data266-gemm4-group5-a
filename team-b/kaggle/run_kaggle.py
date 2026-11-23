"""Team B Kaggle launcher — evaluate a Team B variant without touching Team A assets.

Examples (run from the repo root):

    python team-b/kaggle/run_kaggle.py team-b/variants/base smoke --dry-run
    python team-b/kaggle/run_kaggle.py team-b/variants/analyzer-plan smoke --max-tasks 2
    python team-b/kaggle/run_kaggle.py team-b/variants/diff-critic smoke
    python team-b/kaggle/run_kaggle.py --fetch team-b/variants/base smoke
    python team-b/kaggle/run_kaggle.py --print-verified-runtime
    python team-b/kaggle/run_kaggle.py --check-cli

What it does:
  1. Validates the selected Team B variant offline (harness/validate.py).
     Missing adapter_model.safetensors is allowed only with `--dry-run`; real runs abort.
  2. Stages a PRIVATE Team B dataset `<you>/g5b-agents` containing ONLY:
       - G5B_REPO_MARKER
       - harness/ (shared splits + tooling; runs/ excluded)
       - the full team-b/variants/ tree (all Team B variants present on this checkout)
     Staging every variant avoids concurrent --no-wait races on a single dataset slug.
     It does NOT upload Team A baseline/, variants/, or combined/.
  3. Pushes a private GPU script kernel `<you>/g5b-eval-...` that runs
     team-b/kaggle/kaggle_runner.py (internet off; competition + wheelhouse + model attached;
     NvidiaL4 accelerator; verified Python 3.12 docker_image pin).
  4. Downloads outputs into team-b/kaggle/runs/<variant>/<split>/<UTC>/ and summarizes.

`--dry-run` never calls the Kaggle API, never needs credentials, and writes the staged
dataset + kernel under team-b/kaggle/runs/_dryrun/.

Requires ~/.kaggle credentials only for real uploads (not for --dry-run).
Real pushes require a Kaggle CLI that transmits metadata `docker_image` (kaggle>=2.x;
1.7.4.5 only sends `docker_image_pinning_type` and silently ignores the digest).
"""

from __future__ import annotations

import argparse
import json
import os
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
# Competition wheelhouse ships CPython 3.12 (cp312) wheels; Python 3.13 kernels fail at pip install.
REQUIRED_CPYTHON = (3, 12)
REQUIRED_GPU_COUNT = 4
REQUIRED_GPU_NAME = "L4"

# Verified by a Team B lightweight GPU probe (competition attached, internet off, NvidiaL4).
# Observed: Python 3.12.13, 4× NVIDIA L4. The digest itself is the shared default — teammates
# do not need any personal probe kernel ID or username to run the launcher.
VERIFIED_DOCKER_IMAGE = (
    "gcr.io/kaggle-private-byod/python@"
    "sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461"
)
VERIFIED_PYTHON = "3.12.13"
VERIFIED_RUNTIME_SOURCE = (
    "Team B L4×4 competition GPU probe (Nov 2026): "
    f"python={VERIFIED_PYTHON}, gpu_count={REQUIRED_GPU_COUNT}, "
    f"gpus=NVIDIA L4×{REQUIRED_GPU_COUNT}, machine={DEFAULT_MACHINE}, "
    f"competition={COMPETITION}, internet=off, docker_image={VERIFIED_DOCKER_IMAGE}"
)
# Backward-compatible alias used by older dry-run messaging / tests.
FALLBACK_DOCKER_IMAGE = VERIFIED_DOCKER_IMAGE

# Official docker-python GPU release candidate (GitHub only). Not the Team B default.
CANDIDATE_V173_DOCKER_IMAGE = (
    "gcr.io/kaggle-private-byod/python@"
    "sha256:83f7b285b2fc8e20265817fc233825a31a385718fc4aa75e65caa900d968a378"
)
CANDIDATE_V173_TAG = "gcr.io/kaggle-private-byod/python:v173"
CANDIDATE_V173_PYTHON = "3.12.15"
CANDIDATE_V173_SOURCE = (
    "Kaggle/docker-python GitHub release 'v173 - GPU' (2026-10-30); "
    f"tag {CANDIDATE_V173_TAG}; digest sha256:83f7b285…; "
    f"PYTHON_VERSION={CANDIDATE_V173_PYTHON} from release notes. "
    "Not used as the Team B default — prefer the probe-verified digest above."
)
DOCKER_IMAGE_ENV = "G5B_KAGGLE_DOCKER_IMAGE"
IMAGE_VERIFICATION_ENV = "G5B_KAGGLE_IMAGE_VERIFICATION"
# gpu-probe = the verified L4×4 / Py3.12.13 competition probe above.
VERIFIED_IMAGE_SOURCES = ("gpu-probe", "notebook-pull", "session-python")
ALL_IMAGE_SOURCES = VERIFIED_IMAGE_SOURCES + ("github-release-candidate",)
DEFAULT_IMAGE_VERIFICATION = "gpu-probe"

# Only Team B variant trees + shared harness splits/tooling. Never Team A experiment folders.
# Ignore junk/outputs only. Do NOT ignore *.safetensors: restored adapter weights must
# ship inside the private Kaggle dataset (they stay out of git via the repo .gitignore).
UPLOAD_IGNORE = shutil.ignore_patterns(
    "runs", "results", "__pycache__", "*.pyc", ".DS_Store", "*.zip",
)
ALLOWED_VARIANT_PREFIX = "team-b/variants/"
DRY_RUN: Path | None = None


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


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


def parse_kaggle_cli_version(version_text: str) -> tuple[int, ...] | None:
    """Parse `kaggle --version` / package version strings into an int tuple."""
    m = re.search(r"(\d+(?:\.\d+)+)", version_text)
    if not m:
        return None
    return tuple(int(p) for p in m.group(1).split("."))


def kaggle_cli_reports_docker_image_push_support(version: tuple[int, ...] | None) -> bool:
    """Return True when the installed CLI is expected to transmit metadata docker_image.

    Kaggle API 1.7.4.5 reads docker_image_pinning_type only and silently drops docker_image.
    Support landed in #774 and ships in kaggle 2.x (ApiSaveKernelRequest.docker_image).
    """
    if version is None:
        return False
    return version >= (2, 0, 0)


def probe_kaggle_cli_docker_image_support() -> dict:
    """Inspect the local `kaggle` CLI for docker_image push support (no network)."""
    info: dict = {
        "kaggle_executable": shutil.which("kaggle"),
        "version_text": None,
        "version": None,
        "supports_docker_image_push": False,
        "probe": None,
    }
    if not info["kaggle_executable"]:
        info["probe"] = "kaggle executable not found on PATH"
        return info
    try:
        proc = subprocess.run(
            ["kaggle", "--version"],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=30,
        )
        info["version_text"] = (proc.stdout + proc.stderr).strip()
        info["version"] = parse_kaggle_cli_version(info["version_text"] or "")
    except (OSError, subprocess.TimeoutExpired) as e:
        info["probe"] = f"kaggle --version failed: {e}"
        return info

    # Prefer inspecting the CLI's own package source (same interpreter as the kaggle script).
    exe = Path(str(info["kaggle_executable"])).resolve()
    try:
        shebang = exe.read_text(encoding="utf-8", errors="ignore").splitlines()[0]
        py = shebang[2:].strip() if shebang.startswith("#!") else ""
        if py:
            proc = subprocess.run(
                [
                    py,
                    "-c",
                    "import kaggle.api.kaggle_api_extended as m, pathlib; "
                    "p=pathlib.Path(m.__file__); t=p.read_text(encoding='utf-8', errors='ignore'); "
                    "print(p); print('yes' if 'request.docker_image' in t else 'no')",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
            if len(lines) >= 2:
                info["probe"] = f"cli_package_source:{lines[0]}"
                info["supports_docker_image_push"] = lines[1] == "yes"
                return info
            info["probe"] = f"cli_package_probe_failed:{(proc.stderr or proc.stdout or '').strip()[:200]}"
    except (OSError, subprocess.TimeoutExpired, IndexError) as e:
        info["probe"] = f"cli_package_probe_error:{type(e).__name__}:{e}"

    info["supports_docker_image_push"] = kaggle_cli_reports_docker_image_push_support(info["version"])
    if info["probe"] is None:
        info["probe"] = "version_heuristic"
    return info


def require_kaggle_cli_docker_image_support(*, dry_run: bool) -> dict:
    """Abort real pushes when the local CLI cannot send docker_image."""
    info = probe_kaggle_cli_docker_image_support()
    ver = ".".join(str(x) for x in info["version"]) if info["version"] else "?"
    print(
        f"kaggle CLI: {info['kaggle_executable'] or '(missing)'} "
        f"version={ver} docker_image_push={'yes' if info['supports_docker_image_push'] else 'NO'} "
        f"({info['probe']})"
    )
    if dry_run or info["supports_docker_image_push"]:
        return info
    die(
        "BLOCKER: local Kaggle CLI does not transmit kernel-metadata.json `docker_image`.\n"
        f"Detected: {info.get('version_text') or 'unknown'} ({info.get('probe')}).\n"
        "Kaggle API 1.7.4.5 only sends docker_image_pinning_type (original|latest) and "
        "silently ignores docker_image — that is why Python 3.13 'latest' kernels still appear.\n"
        "Install a modern CLI that sets ApiSaveKernelRequest.docker_image (kaggle>=2.0, "
        "Python >=3.11), e.g.:\n"
        "  python3.12 -m venv ~/.venvs/data266-kaggle-312\n"
        "  source ~/.venvs/data266-kaggle-312/bin/activate\n"
        "  python -m pip install --upgrade pip 'kaggle>=2.0' PyYAML six\n"
        "  hash -r; which kaggle; kaggle --version\n"
        "Then re-run: python team-b/kaggle/run_kaggle.py --check-cli"
    )


def pull_notebook_docker_image(notebook: str = OFFICIAL_NOTEBOOK) -> str:
    """Pull kernel-metadata.json for a public notebook and return its docker_image (if any)."""
    with tempfile.TemporaryDirectory() as tmp:
        kaggle("kernels", "pull", notebook, "-m", "-p", tmp, timeout=120)
        meta_path = Path(tmp) / "kernel-metadata.json"
        image = json.loads(meta_path.read_text()).get("docker_image")
        if not image:
            die(
                f"No docker_image field in metadata for {notebook} "
                "(value was null/missing). Cannot treat this notebook as a verified pin."
            )
        return str(image)


def normalize_image_verification(raw: str | None, *, dry_run: bool) -> str | None:
    value = (raw or os.environ.get(IMAGE_VERIFICATION_ENV, "") or "").strip().lower()
    if not value:
        return None if dry_run else None
    if value not in ALL_IMAGE_SOURCES:
        die(
            f"Invalid --image-verification {value!r}. "
            f"Choose one of: {', '.join(ALL_IMAGE_SOURCES)}"
        )
    return value


def resolve_docker_image(
    explicit: str | None,
    *,
    dry_run: bool,
    image_verification: str | None,
    accept_unverified_image: bool,
) -> tuple[str, str]:
    """Choose the kernel docker_image for metadata.

    Default: the Team B probe-verified Python 3.12.13 / L4×4 digest. Overrides via
    --docker-image / $G5B_KAGGLE_DOCKER_IMAGE still require a verification source.
    Never silently falls back to Kaggle "latest" / Python 3.13.
    """
    image = (explicit or os.environ.get(DOCKER_IMAGE_ENV, "") or "").strip()
    verification = normalize_image_verification(image_verification, dry_run=dry_run)
    using_default = False
    if not image:
        image = VERIFIED_DOCKER_IMAGE
        using_default = True
        if verification is None:
            verification = DEFAULT_IMAGE_VERIFICATION

    src = (
        "default-verified-probe"
        if using_default and not (explicit or "").strip() and not os.environ.get(DOCKER_IMAGE_ENV, "").strip()
        else ("--docker-image" if (explicit or "").strip() else f"${DOCKER_IMAGE_ENV}")
    )

    if image in {CANDIDATE_V173_DOCKER_IMAGE, CANDIDATE_V173_TAG}:
        print(
            f"WARN  {src} is the GitHub v173 candidate, not the Team B probe-verified default. "
            f"Prefer {VERIFIED_DOCKER_IMAGE} ({VERIFIED_RUNTIME_SOURCE})."
        )

    if verification is None:
        # Explicit non-default image without verification source.
        if dry_run:
            verification = DEFAULT_IMAGE_VERIFICATION if image == VERIFIED_DOCKER_IMAGE else "dry-run"
        else:
            die(
                "Real pushes require --image-verification "
                f"({'|'.join(ALL_IMAGE_SOURCES)}) or ${IMAGE_VERIFICATION_ENV}.\n"
                "Verified paths:\n"
                f"  gpu-probe        — default Team B L4×4 / Python {VERIFIED_PYTHON} digest\n"
                "  notebook-pull   — kernels pull of a GPU session that printed Python 3.12.x\n"
                "  session-python  — you confirmed sys.version is 3.12.x on that image in UI\n"
                f"Default image: {VERIFIED_DOCKER_IMAGE}"
            )

    if verification == "dry-run":
        print(f"docker_image ({src}, verification=dry-run): {image}")
        return image, verification

    if verification not in VERIFIED_IMAGE_SOURCES and not accept_unverified_image:
        die(
            "BLOCKER: image is not verified for Team B evaluation.\n"
            f"Requested verification={verification!r} for docker_image={image}.\n"
            f"Use the probe-verified default ({VERIFIED_DOCKER_IMAGE}) with "
            f"--image-verification {DEFAULT_IMAGE_VERIFICATION}, or provide "
            "notebook-pull|session-python evidence for a different digest.\n"
            f"Probe source: {VERIFIED_RUNTIME_SOURCE}\n"
            "Override only for explicit experimentation: --accept-unverified-image."
        )

    if verification == "gpu-probe" and image != VERIFIED_DOCKER_IMAGE:
        die(
            "BLOCKER: --image-verification gpu-probe only applies to the probe-verified digest.\n"
            f"Expected: {VERIFIED_DOCKER_IMAGE}\n"
            f"Got:      {image}\n"
            "Use notebook-pull|session-python for a different image, or omit --docker-image "
            "to use the verified default."
        )

    print(f"docker_image ({src}, verification={verification}): {image}")
    if image == VERIFIED_DOCKER_IMAGE:
        print(f"verified runtime: {VERIFIED_RUNTIME_SOURCE}")
    return image, verification


def normalize_variant(raw: str) -> str:
    # Kaggle is Linux: always use posix paths in RUN_CONFIG (Windows \ breaks agent.yaml lookup).
    variant = raw.replace("\\", "/").strip().strip("/")
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


def validate_variant(variant_dir: Path) -> tuple[list[str], list[str]]:
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
    """Build the private Team B dataset contents under stage/.

    Stages the full team-b/variants/ tree (not only the selected variant) so two
    concurrent --no-wait kernels sharing <you>/g5b-agents cannot lose each other's folder.
    Still never stages Team A baseline/, variants/, combined/, or lora/.
    """
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

    variants_src = REPO / "team-b" / "variants"
    if not variants_src.is_dir():
        die(f"team-b/variants/ missing at {variants_src}")
    if not variant_dir.is_dir():
        die(f"selected variant missing: {variant_dir}")
    shutil.copytree(variants_src, stage / "team-b" / "variants", ignore=UPLOAD_IGNORE)
    if not (stage / variant / "agent.yaml").is_file():
        die(f"selected variant not present after staging: {variant}")

    # Never stage Team A experiment trees at the dataset root
    for forbidden in ("baseline", "variants", "combined", "lora", "docs"):
        if (stage / forbidden).exists():
            die(f"Refusing to stage Team A path {forbidden}/ in Team B dataset")

    staged = sorted(
        p.name for p in (stage / "team-b" / "variants").iterdir() if p.is_dir()
    )
    (stage / "G5B_REPO_MARKER").write_text(
        "data266 group 5 team-b private evaluation snapshot\n"
        f"selected_variant={variant}\n"
        f"staged_variants={','.join(staged)}\n"
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


def kernel_title_for_slug(kernel_slug: str) -> str:
    """Title must slugify to the same kernel slug (Kaggle CLI warns / misbehaves otherwise)."""
    title = kernel_slug
    as_slug = slugify(title)
    if as_slug != kernel_slug:
        die(
            f"Internal error: kernel title {title!r} slugifies to {as_slug!r}, "
            f"expected {kernel_slug!r}."
        )
    return title


def push_kernel(
    user: str,
    kernel_slug: str,
    run_config: dict,
    model: str,
    dataset: str,
    machine: str,
    timeout: int | None,
    *,
    docker_image: str,
) -> str:
    kernel_id = f"{user}/{kernel_slug}"
    title = kernel_title_for_slug(kernel_slug)
    runner = (TB_KAGGLE / "kaggle_runner.py").read_text()
    config_line = "RUN_CONFIG = " + repr(run_config)
    runner, n = re.subn(r"^RUN_CONFIG = .*$", lambda _: config_line, runner, count=1, flags=re.M)
    if n != 1:
        die("RUN_CONFIG line not found in team-b/kaggle/kaggle_runner.py")
    with tempfile.TemporaryDirectory() as tmp:
        kdir = Path(tmp)
        (kdir / "kaggle_runner.py").write_text(runner)
        # Match the successful Team B L4×4 / Py3.12 probe metadata shape: pin docker_image
        # explicitly, set machine_shape + --accelerator NvidiaL4, leave pinning_type unset
        # (the working probe did not include docker_image_pinning_type).
        (kdir / "kernel-metadata.json").write_text(json.dumps({
            "id": kernel_id,
            "title": title,
            "code_file": "kaggle_runner.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": True,
            "enable_tpu": False,
            "enable_internet": False,
            "machine_shape": machine,
            "docker_image": docker_image,
            "dataset_sources": [WHEELHOUSE, dataset],
            "competition_sources": [COMPETITION],
            "kernel_sources": [],
            "model_sources": [MODEL_SOURCE.format(model=model)],
        }, indent=2))
        if DRY_RUN:
            keep_dry_run(kdir, "kernel")
            return kernel_id
        # kaggle>=2.x: --accelerator overrides/sets machine_shape on the save request.
        # 1.7.4.5 rejected this flag; real pushes already require CLI 2.x for docker_image.
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
    print(f"selected variant staged: {'PASS' if (ds / variant / 'agent.yaml').is_file() else 'FAIL'}")
    staged_names = sorted(p.name for p in (ds / "team-b" / "variants").iterdir() if p.is_dir()) if (ds / "team-b" / "variants").is_dir() else []
    print(f"team-b/variants/ staged ({len(staged_names)}): {', '.join(staged_names) or '(none)'}")
    print(f"harness/splits: {'PASS' if (ds / 'harness' / 'splits' / 'smoke.txt').is_file() else 'FAIL'}")
    for bad in ("baseline", "variants", "combined", "lora"):
        present = (ds / bad).exists()
        print(f"Team A path {bad}/ absent: {'PASS' if not present else 'FAIL'}")
    meta = json.loads((kn / "kernel-metadata.json").read_text())
    print(f"kernel private: {'PASS' if meta.get('is_private') else 'FAIL'}")
    print(f"internet off:   {'PASS' if not meta.get('enable_internet') else 'FAIL'}")
    print(f"enable_gpu:     {'PASS' if meta.get('enable_gpu') else 'FAIL'}")
    print(
        f"machine_shape:  "
        f"{'PASS' if meta.get('machine_shape') == DEFAULT_MACHINE else 'FAIL'} "
        f"({meta.get('machine_shape')!r})"
    )
    print(
        f"docker_image:   "
        f"{'PASS' if meta.get('docker_image') == VERIFIED_DOCKER_IMAGE else 'CHECK'} "
        f"({meta.get('docker_image')})"
    )
    print(
        f"pinning_type absent: "
        f"{'PASS' if 'docker_image_pinning_type' not in meta else 'FAIL'} "
        f"(matches successful probe metadata)"
    )
    title_ok = meta.get("title") == meta.get("id", "").split("/")[-1]
    print(f"title==slug:    {'PASS' if title_ok else 'FAIL'} (title={meta.get('title')!r})")
    print(
        f"competition:    "
        f"{'PASS' if meta.get('competition_sources') == [COMPETITION] else 'FAIL'} "
        f"{meta.get('competition_sources')}"
    )
    print(f"datasets:       {meta.get('dataset_sources')}")
    print(f"models:         {meta.get('model_sources')}")
    print(f"push would use: kaggle kernels push --accelerator {meta.get('machine_shape')}")
    runner = (kn / "kaggle_runner.py").read_text()
    print(f"runner uses G5B marker: {'PASS' if 'G5B_REPO_MARKER' in runner else 'FAIL'}")
    print(f"runner avoids G5A marker: {'PASS' if 'G5A_REPO_MARKER' not in runner else 'FAIL'}")
    print(
        f"runner has runtime_preflight: "
        f"{'PASS' if 'def runtime_preflight' in runner else 'FAIL'}"
    )
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
    ap.add_argument("variant", nargs="?", help="Team B variant path, e.g. team-b/variants/base")
    ap.add_argument("split", nargs="?", choices=["smoke", "dev", "train"], help="task split")
    ap.add_argument("--task-ids", nargs="+", default=[], help="run only these instance_ids")
    ap.add_argument("--max-tasks", type=int, default=0, help="first N tasks of the split")
    ap.add_argument(
        "--machine",
        default=DEFAULT_MACHINE,
        help=f"Kaggle machine_shape written into kernel-metadata.json (default {DEFAULT_MACHINE})",
    )
    ap.add_argument(
        "--docker-image",
        default=None,
        help=(
            "Kaggle docker_image digest/tag (or set "
            f"${DOCKER_IMAGE_ENV}). Default: probe-verified "
            f"{VERIFIED_DOCKER_IMAGE} (Python {VERIFIED_PYTHON}, 4×L4)."
        ),
    )
    ap.add_argument(
        "--image-verification",
        default=None,
        choices=list(ALL_IMAGE_SOURCES),
        help=(
            "How the docker_image was verified. Default for the probe digest: "
            f"{DEFAULT_IMAGE_VERIFICATION}. Other digests need notebook-pull|session-python "
            f"(or set ${IMAGE_VERIFICATION_ENV}). github-release-candidate needs "
            "--accept-unverified-image."
        ),
    )
    ap.add_argument(
        "--accept-unverified-image",
        action="store_true",
        help=(
            "Allow github-release-candidate pins (e.g. v173) without notebook verification. "
            "Still subject to CLI docker_image support."
        ),
    )
    ap.add_argument(
        "--print-notebook-docker-image",
        action="store_true",
        help=f"pull {OFFICIAL_NOTEBOOK} metadata, print docker_image, exit (does not push)",
    )
    ap.add_argument(
        "--print-verified-runtime",
        action="store_true",
        help="print the Team B probe-verified Python 3.12 + L4×4 docker_image and exit",
    )
    ap.add_argument(
        "--check-cli",
        action="store_true",
        help="probe local kaggle CLI for docker_image push support and exit (no upload)",
    )
    ap.add_argument(
        "--print-candidate-v173",
        action="store_true",
        help="print the GitHub-documented v173 GPU candidate reference and exit",
    )
    ap.add_argument("--timeout", type=int, help="kernel run-time limit in seconds")
    ap.add_argument("--no-wait", action="store_true", help="push and return; fetch later with --fetch")
    ap.add_argument("--fetch", action="store_true", help="download + summarize the latest run of this kernel")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="stage dataset+kernel under team-b/kaggle/runs/_dryrun; no Kaggle API, no credentials; "
             "missing adapter_model.safetensors is allowed only in this mode",
    )
    args = ap.parse_args()

    if args.print_candidate_v173:
        print(CANDIDATE_V173_DOCKER_IMAGE)
        print(f"tag: {CANDIDATE_V173_TAG}", file=sys.stderr)
        print(f"python: {CANDIDATE_V173_PYTHON}", file=sys.stderr)
        print(f"source: {CANDIDATE_V173_SOURCE}", file=sys.stderr)
        print(
            "STATUS: GitHub candidate only — Team B default is the probe-verified digest "
            f"({VERIFIED_DOCKER_IMAGE}).",
            file=sys.stderr,
        )
        return 0

    if args.print_verified_runtime:
        print(VERIFIED_DOCKER_IMAGE)
        print(json.dumps({
            "docker_image": VERIFIED_DOCKER_IMAGE,
            "python": VERIFIED_PYTHON,
            "machine_shape": DEFAULT_MACHINE,
            "gpu_count": REQUIRED_GPU_COUNT,
            "gpu_name": f"NVIDIA {REQUIRED_GPU_NAME}",
            "competition": COMPETITION,
            "enable_internet": False,
            "image_verification": DEFAULT_IMAGE_VERIFICATION,
            "source": VERIFIED_RUNTIME_SOURCE,
        }, indent=2), file=sys.stderr)
        return 0

    if args.check_cli:
        info = probe_kaggle_cli_docker_image_support()
        print(json.dumps({
            "kaggle_executable": info["kaggle_executable"],
            "version_text": info["version_text"],
            "version": list(info["version"]) if info["version"] else None,
            "supports_docker_image_push": info["supports_docker_image_push"],
            "supports_accelerator_flag": bool(
                info["version"] and info["version"] >= (2, 0, 0)
            ),
            "probe": info["probe"],
            "verified_docker_image": VERIFIED_DOCKER_IMAGE,
            "verified_runtime": VERIFIED_RUNTIME_SOURCE,
            "candidate_v173": CANDIDATE_V173_DOCKER_IMAGE,
            "candidate_status": "not-team-b-default",
        }, indent=2))
        return 0 if info["supports_docker_image_push"] else 2

    if args.print_notebook_docker_image:
        image = pull_notebook_docker_image(OFFICIAL_NOTEBOOK)
        print(image)
        print(
            "NOTE: Prefer the Team B probe-verified digest "
            f"({VERIFIED_DOCKER_IMAGE}). Getting Started may drift or return null.",
            file=sys.stderr,
        )
        return 0

    if not args.variant or not args.split:
        ap.error(
            "variant and split are required unless "
            "--print-notebook-docker-image / --print-verified-runtime / "
            "--check-cli / --print-candidate-v173 is set"
        )

    global DRY_RUN
    variant = normalize_variant(args.variant)
    variant_dir = REPO / variant
    kernel_slug = f"{KERNEL_PREFIX}-{slugify(variant)}-{args.split}"[:50].strip("-")

    if args.dry_run:
        DRY_RUN = TB_KAGGLE / "runs" / "_dryrun"
        DRY_RUN.mkdir(parents=True, exist_ok=True)
        user = "dry-run-user"
    else:
        user = kaggle_user()

    kernel_id = f"{user}/{kernel_slug}"

    if not args.fetch:
        # Image pin + modern CLI are only required when staging/pushing a kernel.
        require_kaggle_cli_docker_image_support(dry_run=bool(args.dry_run))
        docker_image, image_verification = resolve_docker_image(
            args.docker_image,
            dry_run=bool(args.dry_run),
            image_verification=args.image_verification,
            accept_unverified_image=bool(args.accept_unverified_image),
        )

        if args.split == "dev" and (args.task_ids or args.max_tasks):
            print("NOTE: partial dev runs are fine for debugging; log only full-dev scores for selection.")

        struct_problems = structural_checks(variant, variant_dir)
        if struct_problems:
            for p in struct_problems:
                print(f"STRUCT ERROR  {p}")
            print("Fix structural problems before running.")
            return 1
        print("STRUCT CHECKS: PASS")

        errors, warnings = validate_variant(variant_dir)
        for w in warnings:
            print(f"WARN  {w}")
        if errors:
            for e in errors:
                print(f"ERROR {e}")
            # Missing weights: dry-run may continue for packaging checks; real runs must abort
            # so teammates cannot upload a GPU kernel that will fail and burn quota.
            if only_adapter_weight_errors(errors) and args.dry_run:
                print(
                    "VALIDATE: BLOCKED (missing adapter_model.safetensors). "
                    "Dry-run continues for structural staging; restore weights before real Kaggle runs."
                )
            else:
                if only_adapter_weight_errors(errors) and not args.dry_run:
                    print(
                        "Missing adapter_model.safetensors blocks real Kaggle runs. "
                        "Restore sample adapters (see team-b/kaggle/README.md) or use --dry-run for packaging only."
                    )
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
            "docker_image": docker_image,
            "image_verification": image_verification,
            "required_cpython": f"{REQUIRED_CPYTHON[0]}.{REQUIRED_CPYTHON[1]}",
            "required_gpu_count": REQUIRED_GPU_COUNT,
            "required_gpu_name": REQUIRED_GPU_NAME,
            "machine_shape": args.machine,
            "competition": COMPETITION,
            "enable_internet": False,
        }
        push_kernel(
            user,
            kernel_slug,
            run_config,
            model,
            dataset,
            args.machine,
            args.timeout,
            docker_image=docker_image,
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
