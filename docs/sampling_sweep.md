# Sampling sweep plan (Sarvesh, V1 — Nov 14)

**Control:** `variants/dipin-step-budget-v1` (budget 4.5 min / 50 calls; sampling = baseline defaults).  
**Rule:** each trial changes **only** `configs/sampling.yaml` vs that control. Score on **smoke** (10 tasks); pick the best for the Nov 14 Kaggle slot; then log a **dev** score when quota allows.

Submitted candidate folder: `variants/sarvesh-sampling-v1` (update its `sampling.yaml` + 3-line README if a later trial wins).

## Grid (small)

| ID | Folder / note | temperature | top_p | thinking | Smoke first? |
|---|---|---:|---:|---|---|
| C | `dipin-step-budget-v1` (control) | 0.2 | 0.95 | on (budget 4096) | yes (already 2/10 once) |
| A | `sarvesh-sampling-v1` **(current)** | 0.2 | 0.95 | **off** | ✅ full smoke **2/10** (ties control); see `docs/runs/sarvesh-sampling-v1-smoke-full-20261114T031152Z/` |
| B | trial: higher temp | 0.5 | 0.95 | off (if A helps) or on | after A |
| D | trial: lower temp | 0.0 | 0.95 | same as best of A/C | after A |
| E | trial: top_p | 0.2 | 0.8 | same as best so far | optional |

Do not tune on `dev`. If quota is tight: run A with `--max-tasks 2`, then full smoke, then at most one of B/D.

## Commands

```bash
# adapters: copy sample_submission *.safetensors into the variant's adapters/*/ first
python harness/validate.py variants/sarvesh-sampling-v1
python harness/run_kaggle.py variants/sarvesh-sampling-v1 smoke --max-tasks 2
python harness/run_kaggle.py variants/sarvesh-sampling-v1 smoke
python harness/summarize.py harness/runs/sarvesh-sampling-v1/smoke/<stamp> \
  --baseline harness/runs/dipin-step-budget-v1/smoke/<stamp> --csv
```

## Log

| When (UTC) | Trial | Split | Score | Notes |
|---|---|---|---|---|
| 2026-11-14 02:00–02:14 | A thinking-off | smoke max-2 | **1/2** | Quick check only. `docs/runs/sarvesh-sampling-v1-smoke-max2-20261114/` |
| 2026-11-14 02:25–03:12 | A thinking-off | smoke **10** | **2/10** | Ties Dipin V2 control. 4 EMPTY, 4 FAIL, 2 PASS. `docs/runs/sarvesh-sampling-v1-smoke-full-20261114T031152Z/` + `kept_runs\...zip` |

Record each smoke row in `docs/experiment_log.xlsx`: variant, owner Sarvesh, one-line change, smoke score/time, status.
