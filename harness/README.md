# Local evaluation harness (Dipin, due Nov 12)

Accepts a variant folder and a split (`smoke` or `dev`) and saves per-task pass/fail, runtime and run logs.
Running the agent needs an L4×4 GPU, so scored runs happen in a Kaggle notebook (runner coming). The checks below run on any laptop.

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
