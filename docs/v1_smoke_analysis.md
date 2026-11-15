# V1 structured-loop prompt: smoke analysis and provisional matched comparison

*Khushi, Nov 14. Smoke split only (10 tasks, a subset of train). This is **not** a dev result, and it stays separate from the
baseline dev analysis in `docs/error_analysis.md`. One run per arm at n = 10, so this is exploratory evidence only.*

> **Control status:** `dipin-step-budget-v1` is a **provisional** control, pending the team's confirmation. Rule 1 is unchanged.

## Runs

| Run | Variant | Date | Tasks | Resolved | Artifact (git-ignored) |
|---|---|---|---:|---:|---|
| RUN-004 | V1 `khushi-structured-prompt-v1` | Nov 13 | 2 (pilot) | 1 | `harness/runs/variants-khushi-structured-prompt-v1/smoke/20261113T063632Z` |
| RUN-005 | V1 `khushi-structured-prompt-v1` | Nov 14 | 10 | **1** | `.../variants-khushi-structured-prompt-v1/smoke/20261114T190820Z` |
| RUN-006 | Control `dipin-step-budget-v1` (unchanged) | Nov 14 | 10 | **1** | `.../variants-dipin-step-budget-v1/smoke/20261114T201922Z` |

## Were the two arms matched?

| Setting | Control (RUN-006) | V1 (RUN-005) | Same? |
|---|---|---|---|
| Git tree | `82853e5e` (commit `6e5a534`, clean) | `82853e5e` (run_info: `2a00b81` + uncommitted merge; tree verified identical) | Yes |
| Variant files | baseline `system.md`; README | structured `system.md`; README | **Only intended difference** |
| `agent.yaml`, sub-agent, `analyzer.md`, tools | byte-identical | byte-identical | Yes |
| Model | `gemma-4-31b-it-qat-w4a16-ct` | same | Yes |
| Adapters | genuine Kaggle sample (SHA-256 `dcbedd98…`), placed locally, git-ignored | same file | Yes |
| Sampling | 0.2 / 0.95 / 16,384 max output / 4,096 thinking | same | Yes |
| Budget | 4.5 min / 50 calls / 50 turns; 60 s command timeout; 300 s verification | same | Yes |
| Tasks | the same 10 smoke IDs | same | Yes |
| Hardware | 4× L4; vLLM start 420.5 s | 4× L4; 421.5 s | Yes |
| Timing | 19:23–20:18 UTC | 18:13–19:07 UTC | Back-to-back |

## Per-task comparison (C = control, V1 = treatment)

| Task | Control | V1 | Patch (C / V1) | Files in patch (C / V1) | First OK source edit, call # (C / V1) | Time s (C / V1) | Calls (C / V1) | Pre-edit repro runs (C / V1) | Malformed calls (C / V1) | Post-edit checks (C / V1) | Phase 2 (C / V1) | Category (C / V1) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `fastapi_11194` | failed | empty | scratch only / empty | reproduce_issue.py, reproduce_issue_v2.py / — | none / none | 279 / 276 | 30 / 22 | 2 / 6 | 2 / 2 | 0 / 0 | 2 failed, 2 passed / not run | No source change (scratch-only patch) / Timeout, no source edit |
| `fastapi_13537` | **resolved** | **resolved** | source / source | utils.py / utils.py | #10 / #9 | 237 / 203 | 16 / 11 | 1 / 1 | 0 / 0 | 3 / 1 | 2 passed / 2 passed | Resolved / Resolved |
| `fastapi_14609` | failed | failed | source / source | main.py, shared.py / main.py, may_v1.py, shared.py, v1.py, temp_pydantic_v1_params.py | #9 / #10 | 279 / 280 | 16 / 35 | 0 / 0 | 0 / 0 | 0 / 0 | 5 errors / 5 errors | Patch broke import / Patch broke import |
| `fastapi_14962` | failed | empty | source / empty | v2.py / — | #27 / none | 281 / 270 | 27 / 19 | 0 / 1 | 0 / 0 | 0 / 0 | 2 errors (missing `inline_snapshot`) / not run | Unscoreable in env (missing test dependency)† / Context-window crash, no patch |
| `fastapi_15763` | failed | failed | source / source | routing.py, reproduce_issue.py / routing.py | #5 / #7 | 281 / 262 | 43 / 30 | 1 / 1 | 0 / 0 | 6 / 3 | 4 failed, 30 passed / 4 failed, 30 passed | Wrong or incomplete fix / Wrong or incomplete fix |
| `requests_7505` | failed | failed | source / source | _types.py, models.py / _types.py | #12 / #9 | 347 / 346 | 24 / 23 | 0 / 0 | 0 / 15 | 0 / 0 | 142 passed, 197 errors (httpbin) / same | Unscoreable in env / Unscoreable in env |
| `rich_3180` | empty | empty | empty / empty | — / — | none / none | 274 / 274 | 4 / 4 | 1 / 1 | 0 / 0 | 0 / 0 | not run / not run | Timeout, no source edit / same |
| `rich_3506` | empty | empty | empty / empty | — / — | none / none | 272 / 274 | 9 / 7 | 0 / 4 | 0 / 0 | 0 / 0 | not run / not run | Timeout, no source edit / same |
| `rich_3782` | failed | empty | scratch only / empty | repro.py / — | none / none | 276 / 274 | 22 / 22 | 1 / 4 | 1 / 1 | 0 / 0 | 1 failed, 24 passed / not run | No source change (scratch-only patch) / Timeout, no source edit |
| `rich_4075` | failed | empty | scratch only / empty | repro.py / — | none / none | 277 / 274 | 37 / 27 | 3 / 6 | 2 / 0 | 0 / 0 | 1 failed, 99 passed / not run | No source change (scratch-only patch) / Timeout, no source edit |

† **Correction (Nov 15, found while analysing the dev run):** the control's `fastapi_14962` was first labelled "patch broke import". Its 2 Phase 2
errors are actually `ModuleNotFoundError: No module named 'inline_snapshot'` while collecting the hidden test files, a test dependency missing from
our evaluator (see `docs/v1_dev_analysis.md`). The task can't pass in this environment whatever the patch. Resolution counts are unchanged.

**Definitions** (applied identically to both arms; script `compare_runs.py`, not committed):
- **First OK source edit:** the first `edit_file`/`write_file` call with status `ok` on a non-scratch, non-test file.
- **Pre-edit repro run:** a `run_command` that runs Python other than pytest before that edit.
- **Post-edit check:** any Python or pytest run after it.
- **Malformed calls:** invented argument names, or "mandatory input parameters not present".

## Summary metrics

| Metric | Control, 10 tasks | V1, 10 tasks | Control, excl. `requests_7505` (9) | V1, excl. `requests_7505` (9) |
|---|---:|---:|---:|---:|
| Resolved | **1** (10%) | **1** (10%) | 1 | 1 |
| Empty patch (harness count) | 2 | 6 | 2 | 6 |
| No source change (empty + scratch-only) | 5 | 6 | 5 | 6 |
| Made a successful source edit | 5 | 4 | 4 | 3 |
| Patch covers every reference source file | 3 | 2 | 2 | 2 |
| Wrong or incomplete source fix, scoreable (source patch, not resolved, excl. environment-blocked)† | 2 | 2 | 2 | 2 |
| Scratch file in final patch | 4 | 0 | 4 | 0 |
| Avg / max time (min) | 4.67 / 5.78 | 4.55 / 5.78 | 4.55 / 4.68 | 4.42 / 4.66 |
| Avg tool calls | 22.8 | 20.0 | 22.7 | 19.7 |
| Session timeout | 9 | 7 | 8 | 6 |
| Context-window crash | 0 | 1 | 0 | 1 |
| Repeated reproduction (≥3 pre-edit runs) | 1 | 4 | 1 | 4 |
| Pre-edit reproduction runs, total | 9 | 24 | 9 | 24 |
| Exact duplicate tool calls, total | 25 | 24 | 20 | 8 |
| Tasks with malformed calls / total malformed calls | 3 / 5 | 3 / 18 | 3 / 5 | 2 / 3 |
| Checked after editing | 2 | 2 | 2 | 2 |
| Ran pytest at all | 1 | 0 | 1 | 0 |
| Called `submit_patch` | 1 | 2 | 1 | 2 |

**Successful-fix rate**, defined as resolved tasks out of tasks with a source patch: control 1/5, V1 1/4. Excluding `requests_7505`: 1/4 and 1/3.

## Observed findings

- **Same resolution.** Both arms resolved only `fastapi_13537`, and every task has the same resolved/unresolved result in both arms (no discordant
  task). Patch outcomes differ on 4 tasks: V1 left `fastapi_11194`, `rich_3782` and `rich_4075` empty where the control produced scratch-only patches,
  and V1 left `fastapi_14962` empty after a context crash where the control produced a source patch.
- **Scratch files:** 0 V1 patches contain a scratch file, against 4 control patches.
- **Reproduction:** V1 made 24 pre-edit reproduction runs in total against 9, and repeated reproduction (3 or more runs) in 4 tasks against 1.
- **Source edits:** 4 V1 tasks made a successful source edit, against 5 for the control.
- **`requests_7505`:** the control's patch touched both reference files and V1's touched one. Neither can be scored (see `docs/httpbin_investigation.md`).
  V1's 15 malformed `edit_file` calls on this task make up 15 of V1's 18 malformed calls.
- **Identical Phase 2 results on two tasks:** `fastapi_14609` (5 collection errors in both arms) and `fastapi_15763` (4 failed / 30 passed in both).

## Interpretation (tentative; one run per arm)

- A single n = 10 run with no discordant task gives **no evidence of superiority or regression** in resolution.
- The scratch-file difference fits V1's explicit "never write scratch files into /workspace" rule, but at n = 10 that link is plausible, not shown.
- The extra reproduction runs and one fewer source edit fit the reproduce step taking budget at 4.5 min. That's a hypothesis to check, not a finding.

## Phase 2 output verification

Dipin's `task_details/` fix works in real runs. In RUN-005 and RUN-006, all 10 tasks saved `task_details/<id>.json`.
Every non-empty patch has its Phase 2 pytest output in `test_output`: 4/4 in V1 and 8/8 in the control. Empty patches skip Phase 2 by design.
"Wrong fix" and "broke other tests" can now be told apart for smoke runs.

Two older runs don't have this output:
- **RUN-004 (Nov 13):** ran before the fix and saved no Phase 2 output.
- **RUN-002 (baseline dev):** also predates the fix, so its 5 failed fixes stay "not separable".

## Context-window limitation

`configs/sampling.yaml` reserves `max_output_tokens: 16384` of the 32,768-token context. Once a prompt grows past about 16.4k tokens, every call fails with
`ContextWindowExceededError`. This happened in V1 twice:
- `fastapi_13537` in RUN-004: the crash came after the edit, which was correct, so the task still resolved.
- `fastapi_14962` in RUN-005: no edit, empty patch.

It didn't happen in the control run. The setting is identical in both arms, so the comparison stays fair. Whether V1's longer prompt (4,576 against 3,888 bytes) or its reproduction loop makes the crash
more likely isn't established from 1 against 0 events. Changing the setting is a sampling change, so it's not ours to make in V1.

## Limitations

- One run per arm at n = 10 on smoke (train tasks). Sampling at temperature 0.2 isn't deterministic, so run-to-run variation is unmeasured.
- The control designation is provisional (team confirmation pending). RUN-003 (Dipin, Nov 10, 2/10) used an older harness revision
  and isn't comparable to RUN-006.
- The metrics are trace-derived heuristics, defined above. Repro and check classification rests on command patterns.
- No dev, Kaggle or leaderboard score is implied.
