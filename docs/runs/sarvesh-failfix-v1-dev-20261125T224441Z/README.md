# Run: sarvesh-failfix-v1 — dev (30 tasks, 2026-11-25)

| Item | Value |
|---|---|
| Variant | fail→fix prompt on `dipin-base-v2` (7 min / 50 calls / 80 turns); only `prompts/system.md` changed |
| Kernel | https://www.kaggle.com/code/sarveshreshimwale/g5a-eval-variants-sarvesh-failfix-v1-dev (v1) |
| Resolved | **6/30 = 20.0%** |
| Time | avg 5.32 min, max 7.16 min |
| Outcomes | 6 PASS, 23 FAIL, 1 EMPTY |
| run_info | git `f53cd1c` dirty=True; 2026-11-25T19:18:12 → 2026-11-25T22:06:35 UTC |

| Task | Result | min | tools | patch |
|---|---|---:|---:|---:|
| fastapi_12942 | FAIL | 7.1 | 36 | 1472 |
| fastapi_13207 | FAIL | 7.1 | 42 | 3398 |
| fastapi_13713 | FAIL | 4.4 | 38 | 2592 |
| fastapi_14077 | PASS | 2.1 | 20 | 2442 |
| fastapi_14186 | FAIL | 6.9 | 14 | 6112 |
| fastapi_14246 | FAIL | 7.1 | 46 | 667 |
| fastapi_14258 | FAIL | 4.2 | 50 | 511 |
| fastapi_14262 | FAIL | 7.1 | 36 | 4085 |
| fastapi_14301 | PASS | 7.1 | 50 | 1644 |
| fastapi_14303 | FAIL | 2.4 | 18 | 740 |
| fastapi_14306 | FAIL | 6.7 | 50 | 4232 |
| fastapi_14356 | FAIL | 5.7 | 50 | 711 |
| fastapi_14492 | PASS | 0.9 | 12 | 388 |
| fastapi_14616 | FAIL | 7.2 | 47 | 2711 |
| fastapi_15588 | FAIL | 3.9 | 23 | 1355 |
| httpx_3672 | FAIL | 7.0 | 29 | 2262 |
| requests_7315 | FAIL | 3.8 | 31 | 521 |
| requests_7427 | FAIL | 6.9 | 29 | 1145 |
| requests_7433 | FAIL | 3.1 | 21 | 583 |
| rich_3052 | FAIL | 4.0 | 19 | 2958 |
| rich_3063 | PASS | 3.9 | 26 | 692 |
| rich_3278 | FAIL | 7.1 | 11 | 317 |
| rich_3521 | EMPTY | 7.1 | 27 | 0 |
| rich_3675 | FAIL | 3.4 | 27 | 720 |
| rich_3718 | PASS | 3.4 | 11 | 766 |
| rich_3905 | PASS | 1.5 | 18 | 626 |
| rich_3930 | FAIL | 7.1 | 30 | 2894 |
| rich_3935 | FAIL | 7.1 | 32 | 1317 |
| rich_4070 | FAIL | 7.1 | 44 | 2806 |
| rich_4076 | FAIL | 7.1 | 47 | 947 |

Full artifacts (local, git-ignored): `harness/runs/variants-sarvesh-failfix-v1/dev/20261125T224441Z/`
