# Team experiment log (markdown mirror)

Canonical sheet may also live as `docs/experiment_log.xlsx` (Khushi). This file is the Sarvesh-updated mirror for runs we can commit without Excel.

| Run ID | Date (UTC) | Variant | Owner | One-line change | Smoke | Dev | Kaggle submit | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| RUN-S01 | 2026-11-14 | `sarvesh-sampling-v1` | Sarvesh | thinking off (`thinking_budget: 0`); V2 budget 4.5 min / 50 calls | **2/10** | — | pending Nov 14 slot | smoke done | Ties `dipin-step-budget-v1` control (2/10). Max-2 check was 1/2. Logs: `docs/runs/sarvesh-sampling-v1-smoke-full-20261114T031152Z/` |
| RUN-S02 | 2026-11-21 | `sarvesh-best-of-n-v2` | Sarvesh | prompt-only single retry after failed targeted check | **2/10** | — | pending reschedule | smoke done | Ties sampling V1 2/10; no clear gain vs control. Logs: `docs/runs/sarvesh-best-of-n-v2-smoke-20261121T200946Z/` |
