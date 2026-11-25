# Run: sarvesh-failfix-v1 — full smoke (10 tasks, 2026-11-25)

| Item | Value |
|---|---|
| Variant | fail→fix prompt on `dipin-base-v2` (7 min / 50 calls / 80 turns); only `prompts/system.md` changed |
| Kernel | https://www.kaggle.com/code/sarveshreshimwale/g5a-eval-variants-sarvesh-failfix-v1-smoke (v1) |
| Resolved | **2/10 = 20.0%** |
| Time | avg 6.25 min, max 7.16 min |
| Outcomes | 2 PASS, 8 FAIL, 0 EMPTY |
| run_info | git `f53cd1c` dirty=True; 2026-11-25T17:55:00 → 2026-11-25T19:06:09 UTC |

| Task | Result | min | tools | patch |
|---|---|---:|---:|---:|
| fastapi_11194 | PASS | 6.7 | 49 | 992 |
| fastapi_13537 | PASS | 3.0 | 13 | 823 |
| fastapi_14609 | FAIL | 7.2 | 39 | 5827 |
| fastapi_14962 | FAIL | 7.2 | 40 | 2468 |
| fastapi_15763 | FAIL | 4.9 | 33 | 1527 |
| requests_7505 | FAIL | 6.4 | 42 | 1194 |
| rich_3180 | FAIL | 7.1 | 35 | 887 |
| rich_3506 | FAIL | 7.1 | 14 | 396 |
| rich_3782 | FAIL | 7.1 | 17 | 1173 |
| rich_4075 | FAIL | 5.9 | 50 | 267 |

Full artifacts (local, git-ignored): `harness/runs/variants-sarvesh-failfix-v1/smoke/20261125T191602Z/`
