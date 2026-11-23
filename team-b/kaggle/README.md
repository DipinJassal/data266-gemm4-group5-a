# Team B — Independent Kaggle Evaluation Workflow

Private Team B launcher for scoring agents under `team-b/variants/` on Kaggle **without** uploading or overwriting Team A’s `g5a-agents` dataset or `g5a-eval-*` kernels.

| Resource | Team A (shared harness) | Team B (this folder) |
|---|---|---|
| Dataset slug | `g5a-agents` | **`g5b-agents`** (private) |
| Kernel prefix | `g5a-eval-...` | **`g5b-eval-...`** (private) |
| Repo marker | `G5A_REPO_MARKER` | **`G5B_REPO_MARKER`** |
| Results | `harness/runs/` | **`team-b/kaggle/runs/`** |
| Launcher | `harness/run_kaggle.py` | **`team-b/kaggle/run_kaggle.py`** |

Do **not** treat this infrastructure as competition code-sharing permission between Kaggle Team A and Team B. Keep uploads private to your account; do not publish competition-developed code until compliance is resolved.

## 1. Kaggle prerequisites

1. Kaggle account phone-verified; competition rules accepted for **Team B** (`GROUP_PROGRAMMING_05_b`).
2. **Modern Kaggle CLI (`kaggle>=2.0`, Python ≥3.11).** API **1.7.4.5 only sends
   `docker_image_pinning_type` and silently ignores `docker_image`** — that path cannot
   pin Python 3.12. Probe with:
   ```bash
   python team-b/kaggle/run_kaggle.py --check-cli
   ```
   Recommended local CLI:
   ```bash
   python3.12 -m venv ~/.venvs/data266-kaggle-312
   source ~/.venvs/data266-kaggle-312/bin/activate
   python -m pip install --upgrade pip 'kaggle>=2.0' PyYAML six
   hash -r; which kaggle; kaggle --version
   ```
   Token in `~/.kaggle/kaggle.json` or `access_token` (**never commit**).
3. Enough L4 GPU quota (L4 counts 2×). Internet is **off** in evaluation kernels.
4. Local clone of this repo on a Team B branch that contains the variant you want to score.
5. **Probe-verified Python 3.12 + L4×4 runtime (default).** The official
   `metric/gemma-4-developer-agent-wheelhouse` ships **cp312** wheels. A Python 3.13
   kernel fails during `install_wheelhouse()` before any Gemma inference. The launcher
   defaults to the Team B competition probe runtime (internet off, `NvidiaL4`):

   | Field | Verified value |
   |---|---|
   | Docker image | `gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461` |
   | Python | 3.12.13 |
   | GPUs | 4 × NVIDIA L4 |
   | Machine / accelerator | `NvidiaL4` (`kaggle kernels push --accelerator NvidiaL4`) |
   | Competition | `gemma-4-developer-agent` |
   | Internet | off |

   ```bash
   python team-b/kaggle/run_kaggle.py --print-verified-runtime
   # optional override:
   # export G5B_KAGGLE_DOCKER_IMAGE='...'
   # export G5B_KAGGLE_IMAGE_VERIFICATION=notebook-pull
   ```

   Metadata matches the successful probe shape: explicit `docker_image`, `enable_internet: false`,
   `machine_shape: NvidiaL4`, competition attached — and **no** `docker_image_pinning_type`
   field. CLI 2.x also passes `--accelerator NvidiaL4`. The launcher refuses unverified
   alternate digests rather than silently falling back to “latest”/3.13. Teammates only need
   the shared digest above (no personal probe kernel ID).

6. **Runtime preflight** (inside the kernel, **before** the ~41-wheel install) hard-fails unless
   CPython 3.12, cp312 wheel tags, and **4 visible NVIDIA L4 GPUs** are present. Expected
   `docker_image` / machine shape are recorded in `RUN_CONFIG` / `run_info.json`.

## 2. Obtain official sample adapters

`*.safetensors` are git-ignored. On a fresh clone, `validate.py` fails until you restore them:

```bash
# Download competition sample_submission (exact -f paths: check Kaggle data tab)
kaggle competitions download gemma-4-developer-agent -p data

# Copy into the variant you will run (example: base)
cp data/sample_submission/adapters/main_lora/adapter_model.safetensors \
  team-b/variants/<name>/adapters/main_lora/
cp data/sample_submission/adapters/tool_lora/adapter_model.safetensors \
  team-b/variants/<name>/adapters/tool_lora/
```

Do **not** commit weights, datasets, or `submission.zip`.

## 3. Prepare Team B private runtime assets

From the **repo root**, with the variant folder present on your current checkout:

```bash
# Offline packaging rehearsal (no credentials, no upload)
python team-b/kaggle/run_kaggle.py team-b/variants/base smoke --dry-run
```

Dry-run writes:

- `team-b/kaggle/runs/_dryrun/dataset/` — staged private dataset (marker + `harness/` + full `team-b/variants/` tree)
- `team-b/kaggle/runs/_dryrun/kernel/` — private script kernel metadata + Team B runner

Confirm the dry-run report shows Team A paths `baseline/`, `variants/`, `combined/` **absent**.
Staging every Team B variant (not only the selected one) keeps concurrent `--no-wait` runs safe on the shared `g5b-agents` dataset slug.

Missing `adapter_model.safetensors` is allowed **only** with `--dry-run`. Real uploads abort until adapters are restored.

## 4. Validate a selected agent

```bash
python harness/validate.py team-b/variants/<name> --zip submission.zip
```

`submission.zip` must have `agent.yaml` at its root. Missing safetensors → validation **BLOCKED** until step 2.

Supported intended paths (present after the matching feature branch is checked out or merged):

- `team-b/variants/base`
- `team-b/variants/analyzer-plan`
- `team-b/variants/diff-critic`

V1 and V2 live on separate feature branches; check out the branch that contains the variant before launching.

## 5. Two-task diagnostic (manual)

```bash
source ~/.venvs/data266-kaggle-312/bin/activate   # kaggle 2.2.5+
python team-b/kaggle/run_kaggle.py --check-cli    # expect supports_docker_image_push: true
python team-b/kaggle/run_kaggle.py team-b/variants/<name> smoke --max-tasks 2
```

Uses your quota. Kernel name pattern: `g5b-eval-team-b-variants-<name>-smoke` (truncated to 50 chars).
Defaults to the probe-verified Python 3.12.13 / L4×4 docker image + `--accelerator NvidiaL4`.

## 6. Full 10-task smoke (manual)

```bash
python team-b/kaggle/run_kaggle.py team-b/variants/<name> smoke
# or non-blocking:
python team-b/kaggle/run_kaggle.py team-b/variants/<name> smoke --no-wait
```

## 7. Retrieve results

```bash
python team-b/kaggle/run_kaggle.py --fetch team-b/variants/<name> smoke
```

Outputs land under `team-b/kaggle/runs/` (git-ignored). The launcher calls `harness/summarize.py` on `harness_results.jsonl`.

## 8. Inspect agent / sub-agent traces

Under a run directory look for:

- `harness_results.jsonl` — per-task summary
- `run_info.json` — budgets, model, git rev
- `task_details/<id>.json` — full swegemma result when available
- swegemma `logs/`, `traces/`, `patches/` if emitted

For `diff-critic`, check critic call count, OK vs problems, and whether a second critic loop occurred (should be none).

## 9. Record experiments

Append a row to `team-b/docs/experiment_log.csv` (`team=B`, clear smoke vs validation labels). Never present Team A scores as Team B results.

## 10. Completed-candidate `dev` evaluation

```bash
# Only after the variant is final — one full run; do not iterate on dev
python team-b/kaggle/run_kaggle.py team-b/variants/<name> dev --no-wait
python team-b/kaggle/run_kaggle.py --fetch team-b/variants/<name> dev
```

Label the score “validation (used for selection)” in the log. Held-out result = Team B Kaggle submission.

## Manual notebook alternative

If you prefer the UI: create a **private** Kaggle script/notebook attached to:

1. Competition `gemma-4-developer-agent`
2. Dataset `metric/gemma-4-developer-agent-wheelhouse`
3. Your private `g5b-agents` dataset (from this launcher)
4. Model `google/gemma-4/Other/gemma-4-31b-it-qat-w4a16-ct/2`

Paste `team-b/kaggle/kaggle_runner.py`, set `RUN_CONFIG` to your variant/split, GPU L4x4, internet **off**. Do not reimplement the agent in the notebook.

## Compliance note

This workflow packages **shared harness splits** (allowed Team B use of shared tooling) plus **your selected Team B variant**. It does not upload Team A `variants/`. Cross-team publication of competition-developed code still requires a resolved sharing policy (Kaggle forum/notebook publication or organizer permission)—branch isolation alone is not enough.
