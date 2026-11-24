# Skills pack V1 (`poushali-skills-pack-v1`): smoke and dev analysis

**Status (Nov 23):** negative on smoke (1/10), but **6/30 on dev**, the team's best local dev score; merged (PR #22) and submitted to Kaggle by Dipin on Nov 23 (ref 58798802, built from `08f7b70`). One dev run with no matched control dev score, so it is the team's best local result, not evidence that the skill helps.

Owner: Poushali. Variant: `dipin-step-budget-v1` plus one skill, `skills/fix-and-verify/SKILL.md`, and one prompt line that tells the agent to load it first.
Control: Khushi's matched control run of `dipin-step-budget-v1` (RUN-006, `docs/v1_smoke_analysis.md`). Same 10 smoke tasks, same budget (4.5 min, 50 tool calls), 4x L4.

## Runs

| Run | Kernel `poushali02/g5a-eval-variants-poushali-skills-pack-v1-*` | Ran (UTC) | Commit (`dirty`) | `SKILL.md` sha256 | Tasks | Resolved | Avg / max min |
|---|---|---|---|---|---|---|---|
| RUN-P01, 2-task check | `-smoke` version 1 | 11-22 01:23 to 01:41 | `0bae175` (false) | `2f3422d7…` | 2 | 2/2 | 4.4 / 4.7 |
| RUN-P02, full smoke | `-smoke` version 2 | 11-22 01:45 to 02:40 | `08f7b70` (false) | `bb7d2d4e…` | 10 | **1/10** | 4.6 / 5.8 |
| RUN-P05, dev | `-dev` version 1 | 11-23 07:24 to 09:33 | `1f57c1d` (true, line endings only) | `bb7d2d4e…` | 30 | **6/30** | 4.0 / 4.7 |

Each hash was taken from the `agent/` folder the kernel itself used, and each uploaded folder matches its commit. `prompts/system.md` is the same in all
three runs (`a94ed048…`). Raw `run_info.json` and `harness_results.jsonl` for each run are in `docs/runs/poushali-skills-pack-v1-*`; the full
traces stay in the git-ignored `harness/runs/` (several MB per run) and can be shared on request.

**Pilot vs full smoke on `fastapi_11194`.** The two runs used different `SKILL.md` versions (above). In the pilot the agent edited
`fastapi/dependencies/utils.py` at 248 s, also wrote `reproduce_bug.py` into the repo, and the task was resolved (the scratch file didn't affect
the hidden tests). In the full run, all 4 of its `write_file` calls (from 219 s on) left out the required `filepath` argument and failed, so
the session timed out with an empty patch. One task in one run each, so this is within normal run-to-run variation.

The 2-task check showed one wrong rule: the skill said "scratch files go in `/tmp`", but `write_file` only writes inside `/workspace`
(`Path traversal detected: '/tmp/repro.py' escapes workspace root`). The agent then wrote `reproduce_bug.py` into the repo and it ended up in
the patch. `08f7b70` changed the rule to "scratch scripts only via `run_command` into `/tmp`" and added "after 10 calls without an edit,
edit the most likely function now". The full smoke ran on that version.

## Full smoke vs control

| Task | Control (RUN-006) | Skills pack | Files in skills-pack patch | First source edit (call, s) | Pre-edit Python runs |
|---|---|---|---|---|---|
| `fastapi_11194` | failed (scratch only) | empty | none | none | 2 |
| `fastapi_13537` | **resolved** | **resolved** | `fastapi/dependencies/utils.py` | #8, 117 s | 1 |
| `fastapi_14609` | failed (source) | empty | none | none | 0 |
| `fastapi_14962` | failed (source)† | empty | none | none | 0 |
| `fastapi_15763` | failed (source) | empty | none (two root `test_*.py` scratch files, stripped as test files) | none | 4 |
| `requests_7505` | failed (source)† | failed (source) | `_types.py`, `models.py` | #9, 111 s | 0 |
| `rich_3180` | empty | empty | none | none | 2 |
| `rich_3506` | empty | empty | none | none | 1 |
| `rich_3782` | failed (scratch only) | failed (scratch only) | `reproduce_issue.py`, `_2`, `_3` | none | 4 |
| `rich_4075` | failed (scratch only) | failed (scratch only) | `repro.py` | none | 8 |

† Can't pass in this environment (missing test dependencies), see CLAUDE.md findings.

| Metric | Control | Skills pack |
|---|---:|---:|
| Resolved | 1 | 1 |
| Empty patch | 2 | 6 |
| Made a source edit | 5 | 2 |
| Scratch-only patch | 3 | 2 |
| Pre-edit Python runs, total | 9 | 22 |
| Skill loaded | n/a | 10/10 |
| Ran pytest | 1 | 1 |
| Avg / max time (min) | 4.67 / 5.78 | 4.6 / 5.8 |

## What it shows

- **Loading works.** With the trigger line, `load_skill("fix-and-verify")` was the first call in 12/12 tasks across both runs (and 30/30 on dev). This is consistent with Team B's observation that the model doesn't load a skill without a prompt line, though we didn't run a no-trigger arm ourselves.
- **Following does not.** The skill's three main rules were broken often: no reproduction script before editing (22 pre-edit Python runs vs 9), no scratch files via `write_file` (3 tasks), first edit by call 10 (only 2 tasks reached a source edit at all, vs 5 in the control).
- **Same tasks, same ceiling.** The one resolved task is the one every arm resolves. `rich_3180` and `rich_3506` are empty in every arm; in this run their median gap between tool calls was 35 s and 91 s (long thinking), so they time out with 4 to 10 calls regardless of instructions.
- **n = 10, one run.** Resolved is 1 vs 1, within run-to-run noise (the control itself scored 2/10 in RUN-003, Dipin's earlier run on an older harness revision; RUN-006 at 1/10 is the matched control). The process metrics point the wrong way, so at this point it was not proposed for submission (changed after the dev run, below).
- **Crashes on smoke: none.** All 6 empty patches and the other 3 unresolved tasks carry the harness error `Agent exceeded session timeout (4.5 min)`, which is the budget cut-off, not a crash; the 10th task (`fastapi_13537`) finished without error. No sandbox, tool or context-window errors. `requests_7505` took 5.8 min wall time, as it did in the control (347 s), also without an error other than the time-out.

## Conclusion on smoke (Nov 22)

On smoke alone this was a documented negative result (rule 7). A skill is a cheap, valid way to ship procedural know-how, and the load trigger is reliable,
but in these 10 tasks the model often did not follow a multi-rule procedure it loaded at the start once the task got long. A tentative
reading, not tested here: limits the harness enforces (the budget in `eval_config.yaml`) or a smaller context per decision (an `agent_tool`
sub-agent) may change behaviour more than further instructions.
The team then scored every variant on dev (RUN-P05 below), which changed the status.

## Dev run (RUN-P05, Nov 23)

Dipin asked every member to score their variants on dev (Nov 22). This run used exactly the files of the full smoke run (`SKILL.md` sha256 `bb7d2d4e…`, checked in the kernel output),
on 4x L4 with the same budget. Kernel, `run_info.json`, `harness_results.jsonl`, file hashes and the `dirty: true` explanation:
`docs/runs/poushali-skills-pack-v1-dev-20261123T191033Z/`. The skill was the first call in 30/30 tasks.

| | Dev (30) | Dev excl. 7 environment-blocked (23) | Empty | Patches with a scratch file | Avg / max min |
|---|---:|---:|---:|---:|---|
| Baseline (1 min / 10 calls) | 2/30 | 2/23 | 20 | n/a | 1.1 |
| Khushi V1 `khushi-structured-prompt-v1` (RUN-007) | 5/30 | 5/23 | n/a | 9 | n/a |
| Bhoomika V1 `bhoomika-lora-patches-v1` (alpha 8) | 5/30 | 5/23 | 4 | n/a | 3.4 |
| **Skills pack V1 (RUN-P05)** | **6/30 (20.0%)** | **6/23 (26.1%)** | 5 | 6 (3 scratch only, incl. blocked `fastapi_13207`) | 4.0 / 4.7 |

Resolved: `fastapi_14077`, `fastapi_14301`, `fastapi_14492`, `fastapi_14616`, `rich_3718`, `rich_3905` (fastapi 4/15, rich 2/11, requests 0/3, httpx 0/1).
The first five are exactly the tasks Khushi's V1 resolved; the extra one is `fastapi_14616`. None of the 7 blocked tasks passed, as expected.
8/30 tasks ran pytest (the baseline ran it in 0/30).

### How the 24 unsuccessful tasks ended

Sources: `harness_results.jsonl` (`error`), the final patch in `submission.csv`, and the Phase 2 `test_output` in `task_details/`. Each task gets one primary label.

| Primary label | Tasks | Count |
|---|---|---:|
| Environment-blocked (missing `dirty_equals` / `inline_snapshot`, or `pytest-httpbin`), from the team's list of 7 | `fastapi_12942`, `13207`, `13713`, `14246`, `14303`, `14356`, `requests_7433` | 7 |
| Environment-blocked, **newly found**: the hidden tests' `tests/utils.py` imports `inline_snapshot` (the patch was also incomplete: `Depends()` has no `scope` argument) | `fastapi_14262` | 1 |
| Empty patch: budget ran out before any source edit | `fastapi_14186`, `rich_3521` | 2 |
| Empty patch: context-window crash (`ContextWindowExceededError`, prompt reached 16,385 tokens + 16,384 requested output) | `rich_3935` | 1 |
| Scratch files only, no source change (a 3rd scratch-only patch, `fastapi_13207`, is counted under environment-blocked) | `rich_3063`, `rich_4076` | 2 |
| Patch broke import (escaped newline characters written into `fastapi/routing.py` as text, syntax error at collection) | `fastapi_14306` | 1 |
| Wrong or incomplete source fix (hidden tests fail or error) | `fastapi_14258`, `fastapi_15588`, `httpx_3672`, `requests_7315`, `requests_7427`, `rich_3052`, `rich_3278`, `rich_3675`, `rich_3930`, `rich_4070` | 10 |
| **Total** | | **24** |

How they ended in time: 19 hit the 4.5 min session time-out (all 19 are unresolved; all 6 resolved tasks finished without error), 1 crashed on the
context window (`rich_3935`), and 4 finished early but wrong (`fastapi_14303`, `fastapi_14356`, `requests_7315`, `rich_3278`).
Scratch files reached 6 final patches (`fastapi_12942`, `fastapi_13207`, `fastapi_14258`, `fastapi_15588` with `verify_sse.py`, `rich_3063`, `rich_4076`).

`fastapi_14262` suggests the blocked list may be 8/30, not 7/30. It was missed before because earlier dev runs left it empty, so Phase 2 never
ran. Not yet confirmed against the reference patch; the 23-task figure above still uses the team's 7.

### Known wording issues in the skill (left as submitted)

- **Reproduction scripts:** section 1 says "do not write a reproduction script before editing" (one inline `python -c` allowed), while section 5
  explains how to create a scratch script in `/tmp`. The intent is "no script before the edit, `/tmp` only after it", but the text doesn't say so,
  and the agent still made 22 pre-edit Python runs on smoke.
- **Baseline prompt overlap:** `prompts/system.md` (from the baseline) also gives its own testing instructions; the skill's section 3 narrows them
  but doesn't replace them.

### Cleanup rule (`rm`)

The skill's section 5 says to delete files you created and never files that existed before. Across all 40 traced tasks (smoke + dev) the agent
ran `rm` 3 times, always on its own scratch files (`rm repro.py test_multidict.py repro_header.py`, `rm /tmp/repro.py /tmp/repro_subtitle.py`,
`rm /tmp/repro.py`), never on a tracked file, and never used `git clean`, `git checkout` or `git restore`. The submitted folder is kept
byte-identical to the evaluated one (`08f7b70`) so the dev score and Kaggle submission stay reproducible. Tighter wording for any later version
or the combined agent: *"Only delete files that `git status --short` lists as untracked (`??`) and that you created in this task, one by exact name.
Never use wildcards, `-r`, `git clean`, `git checkout` or `git restore`, and never delete a tracked file."*

**Reading it carefully:** this is one run, and the gain over the other V1s is one task. The control `dipin-step-budget-v1` still has no dev score,
so the gain can't be credited to the skill alone, and the smoke result (1/10) pointed the other way. It is the best local dev score in the team so
far and was submitted on Nov 23, but it isn't evidence that the skill works. All figures are from our local harness, not Kaggle's official scorer.
