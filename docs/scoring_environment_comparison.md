# How test dependencies are installed: official scorer vs our harness

*Khushi, Nov 15. Read-only investigation of the published swegemma 0.2.11 / adk_eval_core 0.1.0 wheels
(Kaggle dataset `metric/gemma-4-developer-agent-wheelhouse`), the competition's `docker/` and `sandbox/` files, HARNESS_README,
and the official Getting Started notebook. No code changed, no GPU used.*

## Summary

Our harness evaluates exactly like Kaggle's official **Getting Started notebook**. The official **Stage 2 scorer** very likely uses a different, much larger
**private** package cache. So the tasks blocked by missing test packages in our runs (7 dev tasks, plus smoke `requests_7505` and the control's smoke `fastapi_14962`) are probably an
artifact of the **participant-side** setup, not necessarily of official scoring. This is a strong inference from the code and file sizes, not a verified fact.

## The two code paths in swegemma

| Step | Docker sandbox (default; HARNESS_README's "Container B") | Subprocess sandbox (`'Kaggle/notebooks'` per `swegemma/config.py:98`) |
|---|---|---|
| Where tests run | `swebench-sandbox` image (python:3.13-slim + pytest, pytest-timeout, build tools; `docker/Dockerfile.sandbox` / `.public`) | A fresh venv per task, `system_site_packages=True` (`swegemma/sandbox/subprocess.py:37`), so it sees the **host kernel's** Python packages |
| Test-dependency install (`install_test_dependencies`, `harness/container_setup.py:520`) | Runs. `_ensure_container_site_packages` injects **every** wheel under 16 MB from the wheels cache into site-packages, plus larger wheels the workspace imports. Then runs `sandbox/setup.py` | **Skipped entirely**: `if type(docker).__name__ in {'SubprocessManager', 'SubprocessSandbox'}: return` (line 529) |
| Wheels cache (`resolve_wheels_dir`, line 61) | `config.wheels_dir`, else candidates including `/kaggle/input/datasets/metric/gemma-4-developer-agent-metric-data/sandbox/wheels` and `data/competition_data/secret/sandbox/wheels` | Only reached via `/wheels` path rewriting for commands; not used to install test dependencies |

## What each setup uses

| | Our harness (`harness/kaggle_runner.py:273-292`) | Official Getting Started notebook | Official Stage 2 scorer (`scripts/metric.py`, not published) |
|---|---|---|---|
| Sandbox | `sandbox="subprocess"` | `sandbox='subprocess'` | Docker "Container B" (HARNESS_README §8.2) |
| Wheels | `data_dir / "wheels"` (public competition wheels) | `DATA_DIR / 'wheels'` | Unknown. Likely the private `…-metric-data/sandbox/wheels` |
| Test packages available | Host Kaggle image + editable repo install | Same | The injected wheels cache |

**Our harness matches the official participant notebook** on both settings.

## Evidence that the official scorer has more packages than we do

- The public `wheels/` folder holds **124 files, 27.8 MB**, and none of them is `dirty_equals`, `inline_snapshot`, `pytest-httpbin` or `httpbin`.
- The scorer code refers to a **"1.7 GB /wheels tar copy per task"** (`container_setup.py:405-406`) and has a separate path for wheels of 16 MB or more. No public wheel is that large.
- `docker/Dockerfile.public` copies the "open-source public wheels cache only (**zero private wheels** or internal code artifacts)". That implies a private cache exists.
- `metric/gemma-4-developer-agent-metric-data` and `ryanholbrook/gemma4swe-wheelhouses`, both referenced in the code, return **403** (private).

## What remains unverified

- Whether the private cache actually contains `dirty_equals`, `inline_snapshot` and `pytest-httpbin`. We can't list it.
- That official Stage 2 runs the Docker path. That's what HARNESS_README says, but `scripts/metric.py` isn't published.

## Implications

- The **full local 30-task results stand** as measured. They come from our participant-side harness and aren't Kaggle's official competition scores. Every run of ours (baseline RUN-002, V1, control) is affected identically, so within-harness comparisons stay fair.
- The **absolute** dev scores probably understate official scoring by up to the 7 blocked tasks, but only where the agent's fix was also correct. We can't tell which those are without the packages.
- **Options for the team (Dipin's harness, his decision):**
  1. Report a 23-task sensitivity analysis next to every full local 30-task result, never instead of it.
  2. Post on the competition forum asking whether participants' local evaluation is expected to lack these test dependencies.
  3. Re-score existing patches offline with the missing test packages added in a separate diagnostic environment, the same method as the `httpbin` counterfactual. This takes no GPU, but it does mean opening the dev tasks' test files, so it needs a team decision on held-out discipline.
