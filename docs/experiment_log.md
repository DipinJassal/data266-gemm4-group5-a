# Team experiment log (markdown mirror)

Canonical sheet may also live as `docs/experiment_log.xlsx` (Khushi). This file is the Sarvesh-updated mirror for runs we can commit without Excel.

| Run ID | Date (UTC) | Variant | Owner | One-line change | Smoke | Dev | Kaggle submit | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| RUN-S01 | 2026-11-14 | `sarvesh-sampling-v1` | Sarvesh | thinking off (`thinking_budget: 0`); V2 budget 4.5 min / 50 calls | **2/10** | — | pending Nov 14 slot | smoke done | Ties `dipin-step-budget-v1` control (2/10). Max-2 check was 1/2. Logs: `docs/runs/sarvesh-sampling-v1-smoke-full-20261114T031152Z/` |
| RUN-P03 | 2026-11-22 | `poushali-test-runner-v2` | Poushali | `test_runner_agent` sub-agent (run only related tests, 4-line verdict) + step-3 trigger, on V2 budget (commit `8c98ac4`) | **2/10** | — | not proposed | iteration 1 | Avg 4.4 min. Sub-agent called 0/10 (0 of 5 tasks with a source edit); agent verified with repro scripts. Details: `docs/test_runner_v2_analysis.md` |
| RUN-P04 | 2026-11-22 | `poushali-test-runner-v2` | Poushali | same + "next call after the first source edit must be `test_runner_agent`" (commit `41dd0af`) | **1/10** | — | not proposed | negative result | Avg 4.4 min. Called 1/10 (1 of 4 with a source edit): `fastapi_13537`, 3 commands, 15.5 s, PASS, resolved in 2.9 min. Closed, no dev run. |
