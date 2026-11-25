# Run: poushali-skills-pack-v1, dev (30 tasks, 2026-11-23), RUN-P05

| Item | Value |
|---|---|
| Variant | `variants/poushali-skills-pack-v1` (`fix-and-verify` skill + load trigger, on the `dipin-step-budget-v1` budget) |
| Kernel | https://www.kaggle.com/code/poushali02/g5a-eval-variants-poushali-skills-pack-v1-dev (version 1) |
| Agent dataset | `poushali02/g5a-agents` (private), version uploaded for this run |
| Hardware | 4x L4 (`NvidiaL4`), vLLM start 446.6 s |
| Ran | 2026-11-23 07:24:29 to 09:33:20 UTC |
| Budget | 4.5 min / 50 tool calls / 50 turns per task, 60 s per command, 300 s verification |
| Resolved | **6/30 = 20.0%** (6/23 excluding the 7 environment-blocked tasks) |
| Time | avg 4.0 min, max 4.7 min |
| Local folder (git-ignored) | `harness/runs/variants-poushali-skills-pack-v1/dev/20261123T191033Z` (full traces, patches, Phase 2 output) |

Files here: `run_info.json` and `harness_results.jsonl`, copied unchanged from the run output. They contain no credentials; the only paths are
temporary sandbox paths inside error messages.

## Evaluated commit and the `dirty: true` flag

`run_info.json` records `git_rev 1f57c1d, dirty: true`. The variant folder is identical at `08f7b70`, `1f57c1d` and current `main`
(`git diff 08f7b70 1f57c1d -- variants/poushali-skills-pack-v1` is empty). The tree was dirty only in line endings: on Windows
(`core.autocrlf=true`) a fresh checkout turns the files into CRLF, while the smoke run RUN-P02 had uploaded `SKILL.md` with LF. To make the dev run
use exactly the smoke run's bytes, the variant folder was overwritten with the files the RUN-P02 kernel had used
(`harness/runs/variants-poushali-skills-pack-v1/smoke/20261122T024131Z/agent/`) before launching, then restored afterwards.

Checks on the files the dev kernel actually used (from its `agent/` output folder):
- `skills/fix-and-verify/SKILL.md` sha256 `bb7d2d4e14cf9218f10b8895daddb83b487d8426391e3c0e5e6de0a219cd2582`, byte-identical to the git blob at `08f7b70` and to RUN-P02.
- All 10 non-weight files are identical to `08f7b70` after line-ending normalization.
- Adapters: Kaggle's sample `main_lora` / `tool_lora` dummies (git-ignored), the same files as every other team run.

Dipin's Kaggle submission (Nov 23, ref 58798802) was built separately from `08f7b70` with the same `SKILL.md` hash (CLAUDE.md, Kaggle submissions).

| Task | Result | min | tools | patch |
|---|---|---:|---:|---:|
| fastapi_12942 | FAIL | 4.6 | 26 | 2297 |
| fastapi_13207 | FAIL | 4.6 | 19 | 1750 |
| fastapi_13713 | FAIL | 4.6 | 25 | 1581 |
| fastapi_14077 | PASS | 2.5 | 26 | 1854 |
| fastapi_14186 | EMPTY | 4.6 | 13 | 0 |
| fastapi_14246 | EMPTY | 4.6 | 22 | 0 |
| fastapi_14258 | FAIL | 4.7 | 38 | 1772 |
| fastapi_14262 | FAIL | 4.6 | 35 | 1843 |
| fastapi_14301 | PASS | 4.6 | 37 | 642 |
| fastapi_14303 | FAIL | 2.4 | 13 | 740 |
| fastapi_14306 | FAIL | 4.6 | 26 | 2628 |
| fastapi_14356 | FAIL | 4.0 | 18 | 797 |
| fastapi_14492 | PASS | 0.9 | 11 | 388 |
| fastapi_14616 | PASS | 4.7 | 29 | 1169 |
| fastapi_15588 | FAIL | 4.7 | 16 | 3384 |
| httpx_3672 | FAIL | 4.5 | 22 | 2899 |
| requests_7315 | FAIL | 2.2 | 17 | 521 |
| requests_7427 | FAIL | 4.6 | 11 | 1033 |
| requests_7433 | EMPTY | 4.5 | 27 | 0 |
| rich_3052 | FAIL | 4.6 | 10 | 3393 |
| rich_3063 | FAIL | 4.6 | 26 | 842 |
| rich_3278 | FAIL | 4.3 | 5 | 317 |
| rich_3521 | EMPTY | 4.5 | 7 | 0 |
| rich_3675 | FAIL | 4.6 | 43 | 720 |
| rich_3718 | PASS | 2.3 | 14 | 766 |
| rich_3905 | PASS | 1.4 | 14 | 626 |
| rich_3930 | FAIL | 4.6 | 14 | 1624 |
| rich_3935 | EMPTY | 2.8 | 16 | 0 |
| rich_4070 | FAIL | 4.6 | 34 | 4584 |
| rich_4076 | FAIL | 4.6 | 40 | 885 |
