# Run: sarvesh-best-of-n-v2 — full smoke (10 tasks, 2026-11-21)

| Item | Value |
|---|---|
| Variant | prompt-only single retry; budget 4.5 min / 50 calls (same as `dipin-step-budget-v1`) |
| Kernel | https://www.kaggle.com/code/sarveshreshimwale/g5a-eval-variants-sarvesh-best-of-n-v2-smoke (v1) |
| Resolved | **2/10 = 20%** |
| Time | avg 4.32 min, max 4.69 min |
| Outcomes | 2 PASS, 4 FAIL, 4 EMPTY |

| Task | Result | min | tools | patch |
|---|---|---:|---:|---:|
| fastapi_11194 | PASS | 4.6 | 32 | 992 |
| fastapi_13537 | PASS | 3.9 | 12 | 823 |
| fastapi_14609 | FAIL | 2.5 | 8 | 454 |
| fastapi_14962 | EMPTY | 4.6 | 24 | 0 |
| fastapi_15763 | FAIL | 4.7 | 39 | 2412 |
| requests_7505 | EMPTY | 4.5 | 31 | 0 |
| rich_3180 | EMPTY | 4.6 | 10 | 0 |
| rich_3506 | EMPTY | 4.6 | 2 | 0 |
| rich_3782 | FAIL | 4.6 | 21 | 347 |
| rich_4075 | FAIL | 4.6 | 45 | 525 |

Full artifacts (local, git-ignored): `harness/runs/variants-sarvesh-best-of-n-v2/smoke/20261121T200946Z/`
