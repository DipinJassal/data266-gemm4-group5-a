# V1 structured-loop prompt: dev-split evaluation (RUN-007)

*Khushi, Nov 14–15. Held-out **dev** split, 30 tasks, one complete run. Kept separate from the baseline dev analysis
(`docs/error_analysis.md`) and the smoke analysis (`docs/v1_smoke_analysis.md`). Dev reference patches were **not** inspected:
patch categories come only from each final patch and its Phase 2 test output. Nothing here was used to change the V1 prompt.*

## Headline

**Full local dev result: 5/30 (16.7%).** This is measured with our participant-side harness, not Kaggle's official competition score. Resolved:
- fastapi 3/15: `fastapi_14077`, `fastapi_14301`, `fastapi_14492`
- rich 2/11: `rich_3718`, `rich_3905`
- requests 0/3
- httpx 0/1

This is **not** a controlled improvement over the baseline's 2/30. The baseline ran at **1 min / 10 calls**, V1 at **4.5 min / 50 calls**,
and the matched control (`dipin-step-budget-v1`) has no dev score. The 3-task difference can't be split between the budget and the prompt.

## Run identity (verified from `run_info.json` and the kernel outputs)

| Item | Value |
|---|---|
| Kernel | `khushidonda/g5a-eval-variants-khushi-structured-prompt-v1-dev`, version 1 (private, internet off, NvidiaL4, pinned image) |
| Timing | started 20:50:39, finished 23:01:43 UTC, Nov 14; vLLM start 424.5 s |
| Code | commit `6e5a534`, `dirty: false`, tree `82853e5e`; uploaded agent byte-identical to the committed `variants/khushi-structured-prompt-v1/` |
| Model / GPUs | `gemma-4-31b-it-qat-w4a16-ct`, 4 GPUs |
| Adapters | genuine Kaggle sample (`dcbedd98…`) |
| Sampling | 0.2 / 0.95 / 16,384 max output / 4,096 thinking |
| Budget | 4.5 min / 50 calls / 50 turns; 60 s per command; 300 s verification |
| Tasks | 30/30 present, same IDs and order as `harness/splits/dev.txt` (also the same 30 as the baseline's RUN-002) |
| Evidence | 30/30 `task_details/`, 30/30 traces; Phase 2 `test_output` for all 22 non-empty patches |
| Artifact | `harness/runs/variants-khushi-structured-prompt-v1/dev/20261114T231957Z/` (git-ignored) |

The kernel completed normally. The local downloader timed out once (600 s cap) and the outputs were then fetched download-only. There was no relaunch.

## Environment-blocked tasks (important for every variant)

**7 of 30 dev tasks can't pass in our evaluator, whatever the patch:**
- **6 fastapi tasks:** the hidden test file fails to import during collection with `ModuleNotFoundError`:
  - `dirty_equals`: `fastapi_12942`, `fastapi_13713`, `fastapi_14303`, `fastapi_14356`
  - `inline_snapshot`: `fastapi_13207`, `fastapi_14246`

  Neither package is among the 124 competition wheels. Test files are reset before scoring, so no patch can change this.
- **`requests_7433`:** 142 passed, 195 errors, and **every** error is the `httpbin` recursive-fixture error (`docs/httpbin_investigation.md`).
  Resolution needs 0 errors, so the task can't pass in this environment. This confirms on a dev task what that document had inferred.
  Its reference patch and test patch were not opened.

The same problem also hit one smoke task: the control's `fastapi_14962` in RUN-006 (`inline_snapshot`). It was mislabelled as "patch broke import" and is corrected here and in the workbook.

**Why, and the caveat** (full investigation: `docs/scoring_environment_comparison.md`):
- Our runner evaluates with swegemma's **subprocess** sandbox, exactly like Kaggle's official Getting Started notebook. In that mode swegemma
  **skips test-dependency installation entirely** (`swegemma/harness/container_setup.py:529`), so tests see only the kernel's own packages.
- The official Stage 2 scorer uses the Docker path, which injects a wheels cache. The code points to a private, ~1.7 GB cache, against the public
  27.8 MB wheels. Kaggle's official scoring very likely has these packages, but that's **not verified**.
- The baseline's RUN-002 used the same runner, so these 7 tasks were equally unpassable for it. Comparisons between our runs stay fair.

**Full local result vs sensitivity analysis:**

| | Tasks | V1 resolved |
|---|---:|---:|
| **Full local dev result (all 30 dev tasks)** | 30 | **5 (16.7%)** |
| Sensitivity analysis: excluding seven tasks blocked by missing dependencies in our participant-side scoring environment | 23 | 5 (21.7%) |

Neither figure is Kaggle's official competition score. The sensitivity figure is **not** a replacement score and must not replace 5/30. Its limitations:
- it assumes the blocked tasks are unscoreable for everyone
- it can't say whether V1's patches on the 5 blocked tasks with a source change were correct
- the baseline's equivalent can't be computed the same way, because RUN-002 saved no Phase 2 output, though both baseline resolves are in the scoreable 23

If Kaggle's official scorer does have the missing packages (unverified), any of those 5 patches could count there.

## Summary metrics (all 30 tasks)

| Metric | Value |
|---|---|
| Resolved | **5/30 (16.7%)** |
| Empty patch (harness) | 8/30 |
| Scratch-only patch (no source change) | 3/30 |
| No source change at all | 11/30 |
| Made a successful source edit / final patch has a source change | 19/30 / 19/30 |
| Source patch, not environment-blocked, not resolved (wrong or incomplete fix) | 9 |
| Successful-fix rate (resolved ÷ source patches) | 5/19; 5/14 excluding environment-blocked source patches |
| Patches containing a scratch file (`reproduce_issue.py`, `repro.py`) | **9/30**, incl. resolved `rich_3905` |
| Avg / median / max time (min) | 4.08 / 4.58 / 4.67 |
| Avg / median tool calls | 22.7 / 22.5 |
| Time to first successful source edit | mean 116 s, median 109 s; median call #8; 11 of 19 within the prompt's ~10-call target |
| Session ended by timeout | 21/30 |
| Context-window crashes | **2** (`fastapi_14186`, `rich_3930`), both with no patch |
| Repeated reproduction (≥3 Python runs before the first edit) | 8/30; 77 pre-edit reproduction runs in total (29 in `rich_3278` alone) |
| Exact duplicate tool calls (total) | 88 |
| Tasks with malformed tool calls / total | 11/30 / 41 (20 in `httpx_3672`) |
| Checked after editing / ran pytest at all | 14/30 / 3/30 |
| Called `submit_patch` | 7/30 (`rich_3905` resolved without submitting; the harness scored its diff) |

**Primary category (sums to 30):**
- Resolved: 5
- Wrong or incomplete fix: 9
- Timeout with no source edit: 6
- Unscoreable, missing test dependency: 4
- Scratch-only patch: 3
- Context-window crash, no patch: 2
- Unscoreable, `httpbin`: 1

`fastapi_12942` and `fastapi_14246` are scratch-only patches **and** environment-blocked. The "Env-blocked" column marks all 7.

## Per-task results

`*` = scratch file in the final patch. "Post-edit checks (pytest)" = Python or pytest runs after the first successful source edit (of which pytest).

| # | Task | Result | Patch type | Files in patch | Time s | Calls | First OK source edit | Pre-edit repro runs | Dup. calls | Malformed | Post-edit checks (pytest) | Ctx crash | Phase 2 | Primary category | Env-blocked |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `fastapi_12942` | failed | scratch-only | reproduce_issue.py* | 278 | 25 | none | 4 | 0 | 0 | 0 (0) | no | 1 error [missing test dependency: dirty_equals] | No source change (scratch-only patch) | **yes** |
| 2 | `fastapi_13207` | failed | source, not resolved | v2.py, reproduce_issue.py* | 278 | 32 | #20 @176.2s | 3 | 10 | 2 | 4 (0) | no | 1 error [missing test dependency: inline_snapshot] | Unscoreable in env (missing test dependency) | **yes** |
| 3 | `fastapi_13713` | failed | source, not resolved | applications.py | 278 | 33 | #18 @140.5s | 0 | 9 | 9 | 0 (0) | no | 1 error [missing test dependency: dirty_equals] | Unscoreable in env (missing test dependency) | **yes** |
| 4 | `fastapi_14077` | **resolved** | valid (resolved) | tutorial005.py, exception_handlers.py, utils.py | 185 | 25 | #8 @65.1s | 0 | 1 | 0 | 1 (1) | no | 3 passed | Resolved | no |
| 5 | `fastapi_14186` | empty | empty | — | 232 | 8 | none | 0 | 0 | 0 | 0 (0) | yes | not run | Context-window crash, no patch | no |
| 6 | `fastapi_14246` | failed | scratch-only | reproduce_issue.py* | 278 | 31 | none | 5 | 4 | 0 | 0 (0) | no | 2 errors [missing test dependency: inline_snapshot] | No source change (scratch-only patch) | **yes** |
| 7 | `fastapi_14258` | failed | source, not resolved | routing.py | 280 | 39 | #20 @165.7s | 2 | 0 | 0 | 0 (0) | no | 1 failed | Wrong or incomplete fix | no |
| 8 | `fastapi_14262` | empty | empty | — | 276 | 36 | none | 0 | 10 | 1 | 0 (0) | no | not run | Timeout/budget, no source edit | no |
| 9 | `fastapi_14301` | **resolved** | valid (resolved) | utils.py | 140 | 17 | #11 @97.9s | 1 | 1 | 1 | 1 (0) | no | 11 passed | Resolved | no |
| 10 | `fastapi_14303` | failed | source, not resolved | utils.py | 278 | 22 | #4 @77.8s | 1 | 2 | 0 | 6 (0) | no | 1 error [missing test dependency: dirty_equals] | Unscoreable in env (missing test dependency) | **yes** |
| 11 | `fastapi_14306` | empty | empty | — | 275 | 41 | none | 0 | 9 | 1 | 0 (0) | no | not run | Timeout/budget, no source edit | no |
| 12 | `fastapi_14356` | failed | source, not resolved | utils.py, reproduce_issue.py*, reproduce_issue_header.py* | 278 | 26 | #21 @230.9s | 1 | 1 | 1 | 2 (0) | no | 1 error [missing test dependency: dirty_equals] | Unscoreable in env (missing test dependency) | **yes** |
| 13 | `fastapi_14492` | **resolved** | valid (resolved) | tutorial001_1_py39.py | 49 | 8 | #3 @18.4s | 0 | 1 | 0 | 0 (0) | no | 2 passed | Resolved | no |
| 14 | `fastapi_14616` | failed | source, not resolved | shared.py, v2.py, reproduce_issue.py* | 278 | 24 | #12 @88.7s | 1 | 4 | 0 | 5 (0) | no | 3 failed, 1 passed | Wrong or incomplete fix | no |
| 15 | `fastapi_15588` | failed | source, not resolved | sse.py | 280 | 11 | #3 @183.7s | 0 | 1 | 0 | 0 (0) | no | 6 failed, 18 passed | Wrong or incomplete fix | no |
| 16 | `httpx_3672` | empty | empty | — | 271 | 13 | none | 0 | 10 | 20 | 0 (0) | no | not run | Timeout/budget, no source edit | no |
| 17 | `requests_7315` | failed | source, not resolved | adapters.py | 273 | 29 | #11 @108.9s | 4 | 3 | 2 | 5 (2) | no | 1 failed | Wrong or incomplete fix | no |
| 18 | `requests_7427` | failed | source, not resolved | repro.py*, utils.py | 274 | 22 | #8 @126.1s | 1 | 1 | 2 | 2 (0) | no | 7 failed, 209 passed, 13 skipped | Wrong or incomplete fix | no |
| 19 | `requests_7433` | failed | source, not resolved | models.py | 187 | 12 | #5 @29.3s | 0 | 0 | 0 | 1 (0) | no | 142 passed, 1 skipped, 1 xfailed, 195 errors [httpbin fixture errors] | Unscoreable in env (httpbin) | **yes** |
| 20 | `rich_3052` | failed | source, not resolved | reproduce_issue.py*, prompt.py | 275 | 17 | #7 @125.4s | 1 | 1 | 1 | 1 (0) | no | 1 failed, 6 passed | Wrong or incomplete fix | no |
| 21 | `rich_3063` | empty | empty | — | 273 | 14 | none | 11 | 0 | 0 | 0 (0) | no | not run | Timeout/budget, no source edit | no |
| 22 | `rich_3278` | empty | empty | — | 273 | 30 | none | 29 | 4 | 0 | 0 (0) | no | not run | Timeout/budget, no source edit | no |
| 23 | `rich_3521` | failed | source, not resolved | segment.py | 275 | 13 | #10 @261.0s | 5 | 2 | 1 | 3 (0) | no | 4 failed, 55 passed | Wrong or incomplete fix | no |
| 24 | `rich_3675` | failed | source, not resolved | console.py | 227 | 22 | #17 @134.1s | 1 | 2 | 0 | 3 (0) | no | 1 failed, 98 passed | Wrong or incomplete fix | no |
| 25 | `rich_3718` | **resolved** | valid (resolved) | panel.py | 85 | 8 | #4 @55.9s | 1 | 0 | 0 | 2 (1) | no | 13 passed | Resolved | no |
| 26 | `rich_3905` | **resolved** | valid (resolved) | repro.py*, progress.py | 276 | 44 | #6 @52.8s | 1 | 6 | 0 | 2 (0) | no | 39 passed | Resolved | no |
| 27 | `rich_3930` | empty | empty | — | 168 | 8 | none | 0 | 0 | 0 | 0 (0) | yes | not run | Context-window crash, no patch | no |
| 28 | `rich_3935` | failed | scratch-only | repro.py* | 275 | 14 | none | 3 | 2 | 0 | 0 (0) | no | 2 failed, 20 passed | No source change (scratch-only patch) | no |
| 29 | `rich_4070` | failed | source, not resolved | logging.py | 278 | 34 | #3 @67.5s | 0 | 3 | 0 | 0 (0) | no | 3 failed, 121 passed | Wrong or incomplete fix | no |
| 30 | `rich_4076` | empty | empty | — | 273 | 23 | none | 2 | 1 | 0 | 0 (0) | no | not run | Timeout/budget, no source edit | no |

## Compared with the baseline dev run (RUN-002): descriptive only

| | Baseline (RUN-002) | V1 (RUN-007) |
|---|---|---|
| Budget | 1 min / 10 calls / 50 turns | 4.5 min / 50 calls / 50 turns |
| Prompt | sample prompt | structured-loop prompt |
| Resolved | 2/30 (`fastapi_14492`, `rich_3905`) | 5/30 (the same two + `fastapi_14077`, `fastapi_14301`, `rich_3718`) |
| Empty patch (harness) | 20 | 8 |
| Avg time / task | 1.09 min | 4.08 min |
| Phase 2 output saved | no | yes |

V1 resolved every task the baseline resolved. In the baseline, the three newly resolved tasks were labelled:
- `fastapi_14077`: wrong fix or broke tests
- `fastapi_14301` and `rich_3718`: empty or invalid diff

**Two changes separate these runs**, a 4.5× budget and a new prompt, so the +3 can't be credited to the prompt. A dev run of the matched
control (`dipin-step-budget-v1`, same tree and settings) is needed for that. It's listed as Dipin's open task in CLAUDE.md.

## Observed findings

- **Patch production:** compared with baseline dev, many more tasks end with a source change (19/30). 9 of those don't pass, and 5 are environment-blocked.
- **Scratch files:** the smoke result (0/10 patches with scratch files) **did not replicate**. 9/30 dev patches contain `reproduce_issue.py` or `repro.py`.
  The prompt's "never write into /workspace" rule is not reliably followed.
- **Reproduction loops:** 8 tasks ran 3 or more reproductions before editing. Two (`rich_3063`, `rich_3278`) ended empty after 11 and 29 reproduction runs.
- **Context window:** 2 crashes, both ending with no patch. This is the same 16,384-token output reservation seen in smoke (1 crash in each of RUN-004 and RUN-005).
- **Malformed calls:** 41 in 11 tasks. `httpx_3672` alone had 20 and ended empty.
- **Testing:** 14 tasks checked their work after editing, but only 3 ran pytest. 4 of the 5 resolved tasks checked after editing. `fastapi_14492` finished in 0.8 min without a check.

## Smoke vs dev consistency (V1)

| Metric | Smoke (RUN-005, n=10) | Dev (RUN-007, n=30) |
|---|---|---|
| Resolved | 10% | 16.7% |
| Empty patch | 60% | 27% |
| Scratch file in patch | 0% | 30% |
| Context-window crash | 10% | 6.7% |
| Avg time | 4.55 min | 4.08 min |

## Limitations

- One run, n = 30, temperature 0.2. Run-to-run variation is unmeasured.
- There's no matched control on dev, so no causal claim about the prompt.
- 7 environment-blocked tasks: the full local 30-task result includes them. The 5/23 figure is a sensitivity analysis only. Whether Kaggle's official
  scorer has `dirty_equals`, `inline_snapshot` and `pytest-httpbin` is not verified.
- The categories are heuristics from traces, the final patches and Phase 2 output (definitions as in `docs/v1_smoke_analysis.md`). Without
  reference patches, "wrong file" vs "right file, wrong fix" isn't distinguished on dev.
- The V1 prompt was frozen before this run (commit `6e5a534`). These results must not be used to tune V1 or design V2 (rule 3).

## Rule 6 status for V1

| Item | Status |
|---|---|
| Smoke set runs with no crashes | No harness crash. One agent context-window crash per smoke run (shared output-token setting). **Team judgment** |
| Dev-split score logged next to the baseline | **Done:** Experiment Log V1 row, Dev score 16.7% beside the baseline's 6.7%; Run Details RUN-007 |
| `agent.yaml` validates; zip has `agent.yaml` at root; only allowed tools | Done (`validate.py` OK) |
