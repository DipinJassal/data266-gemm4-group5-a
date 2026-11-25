# Team experiment log (markdown mirror)

Canonical sheet may also live as `docs/experiment_log.xlsx` (Khushi). This file is the Sarvesh-updated mirror for runs we can commit without Excel.

| Run ID | Date (UTC) | Variant | Owner | One-line change | Smoke | Dev | Kaggle submit | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| RUN-S01 | 2026-11-14 | `sarvesh-sampling-v1` | Sarvesh | thinking off (`thinking_budget: 0`); V2 budget 4.5 min / 50 calls | **2/10** | — | pending Nov 14 slot | smoke done | Ties `dipin-step-budget-v1` control (2/10). Max-2 check was 1/2. Logs: `docs/runs/sarvesh-sampling-v1-smoke-full-20261114T031152Z/` |
| RUN-S02 | 2026-11-21 | `sarvesh-best-of-n-v2` | Sarvesh | prompt-only single retry after failed targeted check | **2/10** | — | pending reschedule | smoke done | Ties sampling V1 2/10; no clear gain vs control. Logs: `docs/runs/sarvesh-best-of-n-v2-smoke-20261121T200946Z/` |
| RUN-S03 | 2026-11-25 | `sarvesh-failfix-v1` | Sarvesh | mandatory fail→fix after first source edit (on `dipin-base-v2`) | **2/10** | — | not proposed | smoke done | 0 empty / 8 wrong; avg 6.25 min. Logs: `docs/runs/sarvesh-failfix-v1-smoke-20261125T191602Z/` |
| RUN-S04 | 2026-11-25 | `sarvesh-failfix-v1` | Sarvesh | same | 2/10 (S03) | **6/30** | not proposed | closed (no gain) | Ties base-v2/skills 6/30; lost `fastapi_14616`, gained `rich_3063`. Logs: `docs/runs/sarvesh-failfix-v1-dev-20261125T224441Z/` |
| RUN-P01 | 2026-11-22 | `poushali-skills-pack-v1` | Poushali | `fix-and-verify` skill + load trigger line, on V2 budget (commit `0bae175`) | 2/2 (2-task check) | — | — | check done | Skill loaded 2/2. Found `write_file` can't write `/tmp`; scratch file left in one patch. Fixed in `08f7b70`. |
| RUN-P02 | 2026-11-22 | `poushali-skills-pack-v1` | Poushali | same, revised skill (commit `08f7b70`) | **1/10** | — | not proposed | negative result | Avg 4.6 min. Skill loaded 10/10 but rules often not followed: 6 empty, 2 scratch-only, source edits 2 vs control 5. Details: `docs/skills_pack_v1_analysis.md` |
| RUN-P05 | 2026-11-23 | `poushali-skills-pack-v1` | Poushali | same files as RUN-P02 (commit `08f7b70`) | 1/10 (RUN-P02) | **6/30** (6/23 excl. blocked) | **submitted Nov 23** (ref 58798802) | dev done | Avg 4.0 min. Skill loaded 30/30. Resolved Khushi V1's 5 + `fastapi_14616`. One run; control has no dev score. Details: `docs/skills_pack_v1_analysis.md` |
