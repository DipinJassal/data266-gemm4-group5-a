# Run: sarvesh-sampling-v1 — full smoke (10 tasks, 2026-11-14)

| Item | Value |
|---|---|
| Variant | thinking off; budget 4.5 min / 50 calls (same as `dipin-step-budget-v1`) |
| Kernel | https://www.kaggle.com/code/sarveshreshimwale/g5a-eval-variants-sarvesh-sampling-v1-smoke (v3) |
| Resolved | **2/10 = 20%** (ties control `dipin-step-budget-v1` smoke 2/10) |
| Time | avg 3.0 min, max 4.6 min |

| Task | Result | min | tools | patch |
|---|---|---:|---:|---:|
| fastapi_11194 | PASS | 3.5 | 50 | 2358 |
| fastapi_13537 | PASS | 1.6 | 18 | 2115 |
| fastapi_14609 | FAIL | 1.7 | 24 | 38111 |
| fastapi_14962 | EMPTY | 2.0 | 47 | 0 |
| fastapi_15763 | FAIL | 3.2 | 43 | 2843 |
| requests_7505 | FAIL | 1.7 | 9 | 1048 |
| rich_3180 | EMPTY | 4.5 | 7 | 0 |
| rich_3506 | FAIL | 4.2 | 30 | 3084 |
| rich_3782 | EMPTY | 4.6 | 47 | 0 |
| rich_4075 | EMPTY | 2.8 | 31 | 0 |

Full zip: `kept_runs\sarvesh-sampling-v1-smoke-full-20261114T031152Z.zip`
