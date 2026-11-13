# Local evaluation harness (Dipin, due Nov 12)

Accepts a variant folder and a split (`smoke` or `dev`) and saves per-task pass/fail, runtime and run logs.
Running the agent needs an L4 GPU machine, so scored runs happen in a Kaggle GPU kernel, launched from your laptop.

| Script | Runs on | What it does |
|---|---|---|
| `run_kaggle.py` | laptop | validate → upload repo as private Kaggle dataset → push GPU kernel → wait → download results → summarize |
| `kaggle_runner.py` | Kaggle GPU | wheelhouse install → vLLM → official `swegemma` Evaluator on the split → `harness_results.jsonl` |
| `summarize.py` | laptop | per-task table, resolved %, per repo, time per task, comparison with baseline, experiment-log row |
| `validate.py` | laptop | offline variant check + `submission.zip` builder |
| `make_splits.py` | laptop | rebuilds `splits/` from `data/tasks.jsonl` |

## Score a variant (Kaggle)

One-time setup: install the Kaggle CLI (`uv tool install kaggle --with six` or `pip install kaggle`), accept the
competition rules on Kaggle, and save your API token in `~/.kaggle/access_token`. Runs use **your** Kaggle GPU quota.

```bash
python harness/run_kaggle.py variants/<folder> smoke --max-tasks 2   # quick end-to-end check first
python harness/run_kaggle.py variants/<folder> smoke                 # 10 tasks: crashes + time per task
python harness/run_kaggle.py variants/<folder> dev                   # 30 tasks: the score you log
python harness/run_kaggle.py variants/<folder> dev --no-wait         # push and come back later:
python harness/run_kaggle.py --fetch variants/<folder> dev           #   ...download + summarize
python harness/run_kaggle.py variants/<folder> smoke --dry-run       # build upload folders only, no Kaggle calls

python harness/summarize.py harness/runs/<variant>/dev/<stamp> --baseline harness/runs/baseline/dev/<stamp> --csv
```

Results land in `harness/runs/<variant>/<split>/<UTC stamp>/` (git-ignored): `harness_results.jsonl` (one line per task:
resolved, wall_seconds, tool_calls, patch_chars, error), `run_info.json` (budgets, model, GPU count, git rev),
`submission.csv` (the patch per task), `task_details/<id>.json` (every field of swegemma's result object, which should include the Phase 2 test output — not yet confirmed; runs from Nov 12 on), plus swegemma's logs and traces. Uncommitted changes are uploaded too; `run_info.json` marks them `dirty`.

Each task runs in turn, exactly as on Kaggle, so time per task is realistic. The first ~10–20 minutes of every
kernel are vLLM start-up, which doesn't count toward task time.

## Validate a variant and build its zip

```bash
python harness/validate.py variants/<owner>-<name>-v1                 # checks only
python harness/validate.py variants/<owner>-<name>-v1 --zip submission.zip
```

Checks: one root `agent.yaml`, allowed file types, no symlinks, < 3 GiB, `!include` paths stay inside the folder,
every agent uses the team model, only harness tools / `agent_tool`, adapters exist, token limits ≤ 32,768,
and warns if `eval_config.yaml` allows more than ~6 minutes per task. Needs `pyyaml`.

## Splits

Built by `python harness/make_splits.py data/tasks.jsonl` (deterministic, seed 266). One task ID per line.

| Split | Tasks | Repos | Use |
|---|---|---|---|
| `splits/dev.txt` | 30 | fastapi 15, rich 11, requests 3, httpx 1 | Scoring only. **Never train or tune on these.** |
| `splits/train.txt` | 99 | fastapi 52, rich 37, requests 10 | Everything not in dev; LoRA training data |
| `splits/smoke.txt` | 10 | fastapi 5, rich 4, requests 1 | Quick crash/runtime checks and sweeps. **Subset of train**, so tuning on smoke never touches dev |

The public set has only one HTTPX task, so it is in dev.
