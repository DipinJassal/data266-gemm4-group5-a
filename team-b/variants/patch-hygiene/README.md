**What changed:** a 6-step pre-submit checklist in `prompts/system.md` (git status/diff, delete scratch files and debug prints, `py_compile` changed files, no test files, non-empty diff); nothing else changed from `base`.
**Why:** targets empty or invalid diffs and dirty patches (Team A found a stray `repro.py` in a baseline patch; 20/30 baseline tasks had no patch).
**Source:** [12] SWE-bench (patch must apply cleanly and only source changes count); [4] SWE-Master (final verification step).

**Results (Team B local harness, not Kaggle scores):**
- Smoke (10 tasks, part of train): 1/10 with the checklist only (4 patches held scratch files); 1/10 with scratch scripts moved to `/tmp` (2 patches held scratch files). Same as Team A's control (1/10, 2/10).
- Dev (30 tasks, one run, validation used for selection): **4/30 = 13.3%**, **4/23 = 17.4%** without the 7 tasks that cannot pass locally. Avg 4.0 min per task. Passes: fastapi_14077, fastapi_14492, rich_3718, rich_3905.
- Finding: 7 of 10 smoke tasks hit the 4.5 min limit before `submit_patch`, so the checklist rarely runs. Time, not patch hygiene, is the bottleneck.
- Compared with the base agent on the same dev split (7/30, 7/23): patch-hygiene is **3 tasks worse**. Its 4 passes are a subset of the base's 7. The 3 tasks it lost (fastapi_14301, rich_3063, rich_3278) all hit the 4.5 min timeout. With one run each this is not a significant difference, but there is no sign of a gain.
- The base agent was then submitted to Kaggle and scored **0.10** (held-out), so patch-hygiene was not submitted.
- Decision: **not promoted**. Patch-hygiene is left out of the combined agent.
