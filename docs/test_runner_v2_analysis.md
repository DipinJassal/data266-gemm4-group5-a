# Test-runner V2 (`poushali-test-runner-v2`): smoke analysis

Owner: Poushali. Variant: `dipin-step-budget-v1` plus one `agent_tool` sub-agent, `test_runner_agent`, and a prompt trigger that tells the coder to call it.
Control: `dipin-step-budget-v1` unchanged (Khushi's matched RUN-006, 1/10; RUN-003, Dipin's Nov 10 run on an older harness revision, 2/10). Same 10 smoke tasks, same budget (4.5 min, 50 tool calls), 4x L4.

## The sub-agent

- `sub_agents/test_runner.yaml`: model `gemma-4-31b-it-qat-w4a16-ct`, adapter `tool_lora`, tool `run_command` only, its own sampling file with a 512-token thinking budget.
- `prompts/test_runner.md`: at most 3 commands (find related tests with `git diff --name-only` + `grep -rl`, run only those with `pytest -q -x --tb=short | tail -40`, optionally rerun one test with `-k`), then a 4-line report: `RESULT: PASS | FAIL | BLOCKED | NO_TESTS`, `TESTS`, `FAILURE`, `CAUSE`. `BLOCKED` covers missing test dependencies, so the coder doesn't treat them as its own bug.
- `skip_summarization: true`, so the coder sees only the 4-line report, not the raw test output.

## Runs

| Run | Kernel | Ran (UTC) | Commit (`dirty`) | `prompts/system.md` sha256 | `prompts/test_runner.md` sha256 | Trigger in `prompts/system.md` | Resolved | Avg / max min |
|---|---|---|---|---|---|---|---|---|
| RUN-P03 | `poushali02/g5a-eval-variants-poushali-test-runner-v2-smoke` version 1 | 11-22 03:20 to 04:13 | `8c98ac4` (false) | `59d0767d…` | `e0e3c043…` | step 3: "after your source edit, call `test_runner_agent` once" | **2/10** | 4.4 / 4.7 |
| RUN-P04 | same kernel, version 2 | 11-22 04:26 to 05:19 | `41dd0af` (false) | `02247d70…` | `e0e3c043…` | also in step 2: "your next tool call after your first successful source edit must be `test_runner_agent`" | **1/10** | 4.4 / 4.7 |

Hashes are of the files in each kernel's own `agent/` output folder and match the local files at those commits. Raw `run_info.json` and
`harness_results.jsonl` for both runs are in `docs/runs/poushali-test-runner-v2-smoke-p03-20261122T041417Z/` and `...-p04-20261122T052004Z/`;
the full traces stay in the git-ignored `harness/runs/` and can be shared on request.

**How the runs ended (from `harness_results.jsonl`):**
- RUN-P03: 7 tasks hit the 4.5 min session time-out, 3 finished without error (both resolved tasks and `rich_3506`). The 3 empty patches
  (`fastapi_14962`, `requests_7505`, `rich_3782`) all ended on the time-out. No crashes.
- RUN-P04: 8 time-outs, 1 finished without error (`fastapi_13537`), and **1 context-window crash**: `rich_3506` (`ContextWindowExceededError`
  after 6 calls, empty patch). The other 2 empty patches (`requests_7505`, `rich_4075`) ended on the time-out. The earlier "no crashes" in
  PR #23 was wrong for this run; it is corrected here.

## Per task

| Task | Control (RUN-006) | RUN-P03 | RUN-P04 | P03 first source edit (call, s) | P04 first source edit (call, s) | `test_runner_agent` calls (P03 / P04) |
|---|---|---|---|---|---|---|
| `fastapi_11194` | failed (scratch only) | **resolved** | failed (scratch only) | #22, 201 s | none | 0 / 0 |
| `fastapi_13537` | **resolved** | **resolved** | **resolved** | #10, 126 s | #9, 138 s | 0 / **1** |
| `fastapi_14609` | failed (source) | failed (source) | failed (source) | #9, 77 s | #6, 64 s | 0 / 0 |
| `fastapi_14962` | failed (source)† | empty | failed (source)† | none | #18, 224 s | 0 / 0 |
| `fastapi_15763` | failed (source) | failed (source + scratch) | failed (source + scratch) | #25, 176 s | #13, 99 s | 0 / 0 |
| `requests_7505` | failed (source)† | empty | empty | none | none | 0 / 0 |
| `rich_3180` | empty | failed (scratch only) | failed (scratch only) | none | none | 0 / 0 |
| `rich_3506` | empty | failed (source) | empty (context-window crash) | #2, 141 s | none | 0 / 0 |
| `rich_3782` | failed (scratch only) | empty | failed (scratch only) | none | none | 0 / 0 |
| `rich_4075` | failed (scratch only) | failed (scratch only) | empty | none | none | 0 / 0 |

† Can't pass in this environment (missing test dependencies, see CLAUDE.md findings).

| Metric | Control (RUN-006) | RUN-P03 | RUN-P04 |
|---|---:|---:|---:|
| Resolved | 1 | 2 | 1 |
| Empty patch | 2 | 3 | 3 |
| Made a source edit | 5 | 5 | 4 |
| Called `test_runner_agent` | n/a | 0/10 | 1/10 |
| Called it, of tasks with a source edit | n/a | 0/5 | 1/4 |
| Ran pytest from the coder | 1 | 0 | 0 |
| Tasks that wrote scratch scripts | n/a | 6 | 4 |
| Avg / max time (min) | 4.67 / 5.78 | 4.4 / 4.7 | 4.4 / 4.7 |

## The one call (RUN-P04, `fastapi_13537`)

The coder edited `fastapi/dependencies/utils.py` at call #9 (138 s) and called `test_runner_agent` with `"fastapi/dependencies/utils.py: _extract_form_body"`.
The sub-agent ran 3 commands (`git diff --name-only; grep -rlE ...`, a second `grep`, then `pytest` on `tests/test_forms_single_param.py` and
`tests/test_multipart_installation.py`: 13 passed) and returned `RESULT: PASS` 15.5 s after the call. The coder called `submit_patch` next
and finished at 2.9 min, the fastest run of this task in any arm (control 3.95 min, RUN-P03 4.1 min). This is the design working end to end: the
coder's context got 4 lines instead of the test output, and the verdict ended the task.

## Known limitations (archival variant, not changed)

- **`BLOCKED` can hide the agent's own bug.** The rule treats any collection error, `ModuleNotFoundError` or `ImportError` "for a package that was
  not changed" as a missing test dependency. If the coder's edit breaks an import inside the package it changed (as in dev `fastapi_14306` for the
  skills pack), the sub-agent is told to check whether that package was changed, but a misjudgment would report `BLOCKED` and send the coder to
  `submit_patch`. In these runs the one report was `PASS`, so this never happened, but a later version should tell the two apart explicitly, for
  example by checking whether the error's traceback passes through a file in `git diff --name-only`.
- **Two testing instructions in the coder prompt.** Step 3 of `prompts/system.md` keeps the baseline's direct-pytest bullets ("Run ONLY targeted
  tests", e.g. `pytest tests/test_target.py -k ...`) next to the new "use `test_runner_agent`" bullet. They don't contradict each other, but they
  offer two ways to test; a later version should keep only one.

## What it shows

- **The sub-agent is cheap and correct when called.** 3 commands, 15.5 s, a right verdict, no extra context for the coder.
- **The coder rarely calls it.** With the step-3 line it was never called (0/10), the same as the baseline's `code_analyzer` (0/12 traced tasks).
  With a "next call must be" line it was called in 1 of the 4 tasks that made a source edit. In the other 3 the agent kept editing
  (fixes that touch several places: `fastapi_14609`, `14962`) or went back to its own `repro.py` (`fastapi_15763`), then ran out of time.
- **The agent never ran pytest itself in either run.** Every check after editing was a hand-written reproduction script, which is also how scratch files keep reaching patches.
- **Scores are within noise.** 2/10 and 1/10 against the control's 1/10 and 2/10. The only task resolved in every run is `fastapi_13537`; P03's extra win (`fastapi_11194`) happened without the tool.

## Conclusion

Closed as a documented negative result (rule 7). No dev run was spent, and it isn't proposed for submission. The mechanism works, but a prompt
line can't make this model call a tool at the right moment: triggers tied to "the first action" work (the V1 skill loaded 12/12), while
triggers tied to a later event ("after your edit") mostly don't. For the combined agent, the sub-agent could be kept with a trigger tied to
`submit_patch` ("call `test_runner_agent` before `submit_patch`"). That's untested, so it isn't recommended without its own smoke run.
