# Run: sarvesh-sampling-v1 — smoke `--max-tasks 2` (2026-11-14)

**Not a score** (2 tasks only). Quick end-to-end check after Windows path fix in the harness.

| Item | Value |
|---|---|
| Variant | `variants/sarvesh-sampling-v1` (thinking off; budget = dipin V2 4.5 min / 50 calls) |
| Kernel | https://www.kaggle.com/code/sarveshreshimwale/g5a-eval-variants-sarvesh-sampling-v1-smoke (v2) |
| Model | `gemma-4-31b-it-qat-w4a16-ct`, 4× L4 |
| Git | `ab0e931` (dirty: local docs + path fix) |
| Resolved | **1/2 = 50%** |
| Time | avg 2.7 min, max 3.7 min; vLLM start 419.5 s |

| Task | Result | min | tools | patch_chars | error |
|---|---|---:|---:|---:|---|
| `fastapi_11194` | FAIL | 3.7 | 49 | 1845 | turns budget (50) |
| `fastapi_13537` | PASS | 1.7 | 13 | 2336 | — |

**Committed here:** `harness_results.jsonl`, `run_info.json` (small).  
**Full artifacts (local, not in git):**  
`C:\Users\019129357\Downloads\genai_final_project\kept_runs\sarvesh-sampling-v1-smoke-max2-20261114T021543Z\`  
and `.zip` next to it. Also under `harness/runs/variants-sarvesh-sampling-v1/smoke/20261114T021543Z/` (git-ignored).
