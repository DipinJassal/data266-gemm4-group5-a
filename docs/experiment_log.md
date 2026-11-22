# Team experiment log (markdown mirror)

Canonical sheet may also live as `docs/experiment_log.xlsx` (Khushi). This file is the Sarvesh-updated mirror for runs we can commit without Excel.

| Run ID | Date (UTC) | Variant | Owner | One-line change | Smoke | Dev | Kaggle submit | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| RUN-S01 | 2026-11-14 | `sarvesh-sampling-v1` | Sarvesh | thinking off (`thinking_budget: 0`); V2 budget 4.5 min / 50 calls | **2/10** | — | pending Nov 14 slot | smoke done | Ties `dipin-step-budget-v1` control (2/10). Max-2 check was 1/2. Logs: `docs/runs/sarvesh-sampling-v1-smoke-full-20261114T031152Z/` |
| RUN-P01 | 2026-11-22 | `poushali-skills-pack-v1` | Poushali | `fix-and-verify` skill + load trigger line, on V2 budget (commit `0bae175`) | 2/2 (2-task check) | — | — | check done | Skill loaded 2/2. Found `write_file` can't write `/tmp`; scratch file left in one patch. Fixed in `08f7b70`. |
| RUN-P02 | 2026-11-22 | `poushali-skills-pack-v1` | Poushali | same, revised skill (commit `08f7b70`) | **1/10** | — | not proposed | negative result | Avg 4.6 min. Skill loaded 10/10 but rules often not followed: 6 empty, 2 scratch-only, source edits 2 vs control 5. Details: `docs/skills_pack_v1_analysis.md` |
