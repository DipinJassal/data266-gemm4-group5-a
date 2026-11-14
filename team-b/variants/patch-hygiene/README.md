**What changed:** a 6-step pre-submit checklist in `prompts/system.md` (git status/diff, delete scratch files and debug prints, `py_compile` changed files, no test files, non-empty diff); nothing else changed from `base`.
**Why:** targets empty or invalid diffs and dirty patches (Team A found a stray `repro.py` in a baseline patch; 20/30 baseline tasks had no patch).
**Source:** [12] SWE-bench (patch must apply cleanly and only source changes count); [4] SWE-Master (final verification step).
