# V2 time-budget-aware prompt (`khushi-anti-looping-v2`): two smoke iterations, a negative result

*Khushi, Nov 15. Smoke split only (10 tasks, a subset of train). No dev run, and no dev data or dev reference patches were used to design or revise V2.
One run per arm at n = 10, so everything here is exploratory. The control `dipin-step-budget-v1` is a **provisional** control pending team
confirmation; rule 1 is unchanged.*

## Headline

- **Neither prompt version made the agent check the time more than once.** Both told the agent to call `get_status()` first and then again later.
  It made the first check (7/10 tasks in iteration 1, 10/10 in iteration 2) and **never made a second one (0/10 in both)**.
- So the halfway and endgame rules, which depend on later checks, **never triggered** in either run. The mechanism V2 was designed around never ran.
- **Neither iteration showed a reliable improvement in resolution.** Resolved: control 1/10, iteration 1 2/10, iteration 2 1/10. Timeouts with no
  successful source edit: 5, 6 and 7. At n = 10 these differences are within run-to-run variation, and they can't be credited to a mechanism that didn't run.
- **Decision:** V2 prompt tuning stops here. It's recorded as an exploratory negative result about *instruction compliance for recurring time checks*.
  It is **not** evidence that time awareness can't help a coding agent (see "What this does and doesn't show").

## 1. Hypothesis

The agent loses tasks by running out of wall-clock time before making a usable source edit, partly because it never knows how much time is left.
If it checked the clock periodically and switched from exploring to editing once half the time was gone, fewer sessions would end with no source edit.

Evidence behind it (control smoke run RUN-006, recomputed from raw traces):

| Observation in RUN-006 | Value |
|---|---|
| Sessions ending on the 4.5-min time limit | 9/10 |
| Timed out with no successful source-edit tool call | 5/10 (`fastapi_11194`, `rich_3180`, `rich_3506`, `rich_3782`, `rich_4075`) |
| `get_status()` calls | 1 in 10 tasks (`fastapi_13537`, at 225 s, after submitting) |
| Share of wall-clock spent executing tools | 20 s of 2,802 s (0.7%); the rest is model generation |

**Mechanism gap:** the harness tells the agent its total allowance ("Time allowance: 4.5 minutes") but never its elapsed time. Its only automatic warning
fires when ≤10 *tool calls* remain (swegemma 0.2.11, `swegemma/tools/base.py`), which sessions of about 20 calls never reach. `get_status()`
reports `agent_elapsed_seconds` and `time_seconds_remaining`. It doesn't count against the tool-call budget, but each call costs one model turn,
and turns count toward the 50-turn cap.

**Source:** [4] Song et al., SWE-Master (arXiv:2602.03411), Sec. 3.4.3 "Budget Awareness". During RL training, the environment tells the agent its
remaining **turn** budget at every turn. V2 is an **adaptation**, not a replication: a **wall-clock** budget that the agent must choose to read through
`get_status()`, prompt only, with no training. The paper's version is pushed to the agent by the environment; ours relies on the model following an
instruction. That difference turned out to be the crux.

## 2. Control and what was held fixed

| | Control RUN-006 | V2 iteration 1 RUN-008 | V2 iteration 2 RUN-009 |
|---|---|---|---|
| Variant / commit | `dipin-step-budget-v1` at `6e5a534` (clean) | `khushi-anti-looping-v2` at **`cfec23d`** | `khushi-anti-looping-v2` at **`af977ad`** |
| Run's recorded code state | `6e5a534`, clean | base `a6c709d` + uncommitted V2 folder (`dirty`); now committed byte-identical as `cfec23d` | `af977ad` (`dirty` only from untracked docs) |
| `prompts/system.md` sha256 (first 16) | `f1cbf7943ee96873` | `03d1e90942a0b89c` | `53662ae179191b8d` |
| `README.md` sha256 (first 16) | (control's) | `f48f8a69b0f043d4` | `76d0bc6192e49d06` |
| Kaggle kernel | `khushidonda/g5a-eval-variants-dipin-step-budget-v1-smoke` v1 | `khushidonda/g5a-eval-variants-khushi-anti-looping-v2-smoke` v1 | same kernel, **v2** |
| Run time (UTC) | Nov 14, 19:23–20:18 | Nov 15, 05:19–06:14 | Nov 15, 18:39–19:31 |
| Artifact (git-ignored) | `harness/runs/variants-dipin-step-budget-v1/smoke/20261114T201922Z/` | `harness/runs/variants-khushi-anti-looping-v2/smoke/20261115T065200Z/` | `harness/runs/variants-khushi-anti-looping-v2/smoke/20261115T193206Z/` |

Identical in all three: model `gemma-4-31b-it-qat-w4a16-ct`; 4× L4 (`NvidiaL4`, tp = 4), internet off; image `python@sha256:37c64f7d…`;
`eval_config.yaml` 4.5 min / 50 tool calls / 50 turns / 60 s command timeout; sampling temperature 0.2, top-p 0.95, max output 16,384, thinking budget 4,096;
the genuine Kaggle sample adapters (`adapter_model.safetensors` sha256 `dcbedd98…`, git-ignored, placed locally); tools, sub-agent, `agent.yaml`; harness code; the 10 smoke tasks.

**Verification:** each run's uploaded agent snapshot (`<artifact>/agent/`) is byte-identical to its commit for all 9 tracked files, plus the two
git-ignored adapter weights. Both V2 commits differ from the control **only** in `prompts/system.md` and `README.md`.

## 3. The interventions (exact text)

Both insert one "Time Budget" section between "Core Objective" and "Workflow" in the control's `prompts/system.md`. Nothing else changes.

**Iteration 1 (`cfec23d`, evaluated as RUN-008):**

```markdown
## Time Budget
You have a hard wall-clock limit and will not be warned before it ends. `get_status()` reports `agent_elapsed_seconds` and `time_seconds_remaining`. It does not use a tool call, but each check costs a turn, so check sparingly:
- Call `get_status()` as your first action, then again after every 8 tool calls.
- If `agent_elapsed_seconds` is greater than `time_seconds_remaining` and you have not yet edited a source file, stop exploring and apply the fix best supported by the code you have already read.
- If fewer than 60 seconds remain, start no new investigation: keep your existing source edit, run at most one quick targeted check, then call `submit_patch`.
- Never make arbitrary or unsupported edits just to beat the deadline.
```

**Iteration 2 (`af977ad`, evaluated as RUN-009):** only the trigger changed.

```diff
-It does not use a tool call, but each check costs a turn, so check sparingly:
-- Call `get_status()` as your first action, then again after every 8 tool calls.
+It does not use a tool call, but each check costs a turn, so check only at these points:
+- Call `get_status()` as your first action. Until you have edited a source file, also call it right before every `run_command`.
```

The halfway rule, the endgame rule and the no-arbitrary-edit guardrail are word-for-word the same. Deliberately excluded from both: anti-repetition
rules, scratch-file cleanup, V1's workflow, and any change to tools, model, sampling or budget. (The folder name `anti-looping` predates the design;
the intervention is time awareness only.)

## 4. Why iteration 2 (decided from smoke evidence only)

Iteration 1's agent followed "first action" (7/10) but never the recurring "every 8 tool calls" (0/10). The working hypothesis was that the model
can't count its own calls. Iteration 2 replaced counting with an **event** trigger the agent always knows: "before every `run_command`, until you have
edited a source file".

The trigger was chosen by replaying candidate rules on the **control's** 10 smoke traces (RUN-006). Each check is assumed to land just before the
triggering call. "Halfway reached" means a check at ≥135 s before the first source edit. First-order only, with behaviour after a check not modelled:

| Candidate trigger (plus a first-action check) | Needs counting? | Could fire halfway rule | Of the 5 no-edit tasks | Extra turns (10 tasks) | Turn-cap risk |
|---|---|---:|---:|---:|---|
| None (what iteration 1 actually got) | no | 0/10 | 0 | 10 | none |
| Every 8 calls (iteration 1 as written) | yes | 5/10 | 4 | 33 | none |
| Before every edit/write | no | 2/10 | 2 | 37 | none |
| Before every `run_command` | no | 7/10 | 5 | 91 | 2 tasks |
| Before Python/pytest commands only | no | 3/10 | 3 | 28 | none |
| **Before every `run_command` until the first source edit (chosen)** | no | **7/10** | **5** | **51** (≈ 5 per task) | 1 borderline (`rich_4075`) |

It was the only counting-free rule that reached all 5 no-edit tasks at moderate cost. It was approved, and run once.

## 5. Results: status-check compliance (the primary question)

| Status-check behaviour | Control RUN-006 | It.1 RUN-008 | It.2 RUN-009 |
|---|---:|---:|---:|
| `get_status()` as the first action (tasks) | 0 | 7 | **10** |
| Tasks with 2 or more checks | 0 | 0 | **0** |
| Checks other than the first action (total) | 1 | 0 | **0** |
| Tasks with a check at ≥135 s | 1 (after submitting) | 0 | **0** |
| Pre-edit `run_command`s directly after a check | 0/66 | 2/70 | 4/81 |
| … excluding the opening check | 0/66 | 0/70 | **0/81** |
| Halfway rule triggered → edit followed | 0 → 0 | 0 → 0 | 0 → 0 |
| Endgame rule triggered → submit followed | (1 seen, after submit) | 0 → 0 | 0 → 0 |

- The few "checked" commands are the opening check that happened to precede a task's first command. In RUN-009, iteration 2's predicted ≈ 51 checks
  became 0 beyond the opening ones.
- **The agent never reasoned about time.** In both V2 runs, no recorded agent message (event type `thinking`) mentions `get_status`, elapsed or remaining
  time, the halfway point or the deadline. The trace's system prompt does contain the evaluated rule text.
- **Cost of a check:** the gap from a check to the agent's next call was 1.4–3.2 s, with one outlier per run (16.8 s in RUN-008, 10.0 s in RUN-009);
  in total 27.9 s and 28.1 s. Each check also used one of the 50 turns.

## 6. Results: outcomes (all 10 tasks, plus a labelled sensitivity analysis)

`requests_7505` and `fastapi_14962` can't be resolved in our local evaluator for *any* variant (section 9). The "excl. 2" columns drop them as a
**sensitivity analysis, not a replacement** for the full result.

**Definitions** (applied identically to all three runs):
- *Source / scratch / test file:* scratch = basename `repro*`, `reproduce*`, `debug*`, `scratch*`, `tmp*`, `check*`, `verify*` ending `.py`;
  test = `test_*`, `conftest.py` or under `tests/`; source = anything else.
- *Successful source-edit tool call:* an `edit_file`/`write_file` on a source file that returned `ok`. This is the pre-registered definition.
- *Source-tree change:* the final patch touches a source file by any means, including `rm` or `sed` through `run_command`.
- *Final patch:* **source** (modifies code) / **source, deletion-only** (every touched source file deleted) / **scratch-only** / **empty**.
- *Substantive source patch:* modifies source code, and the scorer's test run is not a collection/import error.

| Metric | RUN-006 | RUN-008 | RUN-009 | RUN-006 excl. 2 | RUN-008 excl. 2 | RUN-009 excl. 2 |
|---|---:|---:|---:|---:|---:|---:|
| **Resolved** | 1 | 2 | 1 | 1 | 2 | 1 |
| Ended on time limit / turn cap / finished | 9 / 0 / 1 | 7 / 0 / 3 | 7 / 1 / 2 | 7 / 0 / 1 | 6 / 0 / 2 | 5 / 1 / 2 |
| **(a) Time limit, no successful source-edit tool call** (pre-registered; target < 5) | 5 | 6 | **7** | 5 | 5 | 5 |
| (b) Time limit, final patch changes no source file | 5 | 6 | 6 | 5 | 5 | 4 |
| (c) Time limit *or* turn cap, no successful source-edit tool call | 5 | 6 | 8 | 5 | 5 | 6 |
| Tasks with a successful source-edit tool call | 5 | 4 | 2 | 3 | 3 | 2 |
| Final patch changes a source file (any means) | 5 | 4 | 3 | 3 | 3 | 3 |
| Final patch: source / deletion-only / scratch-only / empty | 5 / 0 / 3 / 2 | 4 / 0 / 2 / 4 | 2 / 1 / 2 / 5 | 3 / 0 / 3 / 2 | 3 / 0 / 2 / 3 | 2 / 1 / 2 / 3 |
| Substantive source patch | 4 | 3 | 2 | 2 | 2 | 2 |
| Median time to first source edit, s (n) | 158 (5) | 166 (4) | 122 (2) | 94 (3) | 183 (3) | 122 (2) |
| Tool calls avg / turns total / turns max | 22.8 / 232 / 43 | 19.8 / 212 / 39 | 21.7 / 236 / 50 | 22.1 / 181 / 43 | 19.8 / 169 / 39 | 21.5 / 189 / 50 |
| Turn-cap failures / context-window errors | 0 / 0 | 0 / 0 | 1 / 0 | 0 / 0 | 0 / 0 | 1 / 0 |
| Runtime avg / max (min) | 4.67 / 5.78 | 4.49 / 5.17 | 4.31 / 4.65 | 4.53 / 4.68 | 4.39 / 4.65 | 4.25 / 4.65 |
| Called `submit_patch` | 1 | 3 | 2 | 1 | 2 | 2 |

Tool-call counts include `get_status`, as the harness counts them. Median edit times rest on 2–5 tasks and aren't comparable across arms.
All runs averaged under the ~6-min rule-5 limit.

### Per task

Each cell: final patch; scorer result; first successful source-edit tool call; how the session ended; number of status checks.

| Task | Control RUN-006 | V2 it.1 RUN-008 | V2 it.2 RUN-009 |
|---|---|---|---|
| `fastapi_11194` | scratch-only; tests fail; no edit; time limit; 0 | source; **resolved**; 183 s; finished; 1 | scratch-only; tests fail; no edit; time limit; 1 |
| `fastapi_13537` | source; **resolved**; 158 s; finished; 1 | source; **resolved**; 193 s; finished; 0 | source; **resolved**; 164 s; finished; 1 |
| `fastapi_14609` | source; collection error; 94 s; time limit; 0 | source; collection error; 91 s; time limit; 1 | **source, deletion-only**; collection error; no edit; time limit; 1 |
| `fastapi_14962`† | source; env-blocked; 275 s; time limit; 0 | empty; —; no edit; time limit; 1 | empty; —; no edit; time limit; 1 |
| `fastapi_15763` | source; tests fail; 48 s; time limit; 0 | scratch-only; tests fail; no edit; time limit; 1 | source; tests fail; 79 s; finished; 1 |
| `requests_7505`† | source; env-blocked; 220 s; time limit; 0 | source; env-blocked; 149 s; finished; 0 | empty; —; no edit; time limit; 1 |
| `rich_3180` | empty; —; no edit; time limit; 0 | scratch-only; tests fail; no edit; time limit; 1 | empty; —; no edit; time limit; 1 |
| `rich_3506` | empty; —; no edit; time limit; 0 | empty; —; no edit; time limit; 1 | empty; —; no edit; time limit; 1 |
| `rich_3782` | scratch-only; tests fail; no edit; time limit; 0 | empty; —; no edit; time limit; 1 | empty; —; no edit; time limit; 1 |
| `rich_4075` | scratch-only; tests fail; no edit; time limit; 0 | empty; —; no edit; time limit; 0 | scratch-only; tests fail; no edit; **turn cap**; 1 |

† Blocked in our evaluator (missing `inline_snapshot` / `pytest-httpbin`). "Tests fail" on a scratch-only patch means the scorer ran the tests on unchanged source.

## 7. Failure analysis

- **Compliance, not counting, was the failure.** Iteration 2 removed the counting step and compliance didn't move: still 0/10 tasks with a second check.
  The model reliably executes a one-off instruction tied to the start of the session (10/10). It doesn't execute a standing conditional instruction
  ("before every X while Y") once it's absorbed in the task.
- **`fastapi_14609` (RUN-009): deletion through the shell.** With no time check at any point after the first action, the agent ran, at 268 s (2 s before the limit),
  `rm fastapi/_compat/v1.py fastapi/_compat/may_v1.py fastapi/temp_pydantic_v1_params.py`. The final patch (37,548 characters) only deletes
  those three source files, and test collection then fails (5 errors).
  - It made **no successful source-edit tool call**, so it counts in (a). But it **did change the source tree** (excluded from (b)).
  - It is **not a useful source patch** (excluded from "substantive").
  - This is the kind of unsupported last-second change the prompt's guardrail forbids. It happened without the agent having looked at the clock.
- **`rich_4075` (RUN-009): turn cap.** It hit 50 turns at 269.4 s, with 45 tool calls (including one status check) and 18 commands before any edit, ending
  scratch-only. The single opening check used one of the 50 turns. Without it, the session would very likely have hit the 270 s time limit instead,
  under a second later, with the same patch. The checkpoint simulation flagged this task as the turn-cap risk for a *compliant* iteration 2. In practice
  the cap came from the agent's own reproduction loop.
- **Run-to-run variation is large relative to any effect.** Only 2 of 10 tasks keep the same final-patch class in all three runs: `fastapi_13537` (resolved) and `rich_3506` (empty).
  - `fastapi_11194` was resolved in RUN-008 and scratch-only in both other runs.
  - `fastapi_15763` swung between a source patch (RUN-006, RUN-009) and scratch-only (RUN-008).
  - Neither swing can be linked to the time rules, which never fired.
- **Short, reasoning-heavy sessions:** `rich_3180` and `rich_3506` made 2–9 tool calls in 4.5 minutes in every run. Long generation between calls leaves
  few events for any trigger to attach to.

## 8. What this does and doesn't show

**Shows, for this model, harness and budget (n = 10 per run):**
- prompt-only instructions to re-check `get_status()` were not followed, whether count-based or event-based
- the first-action check was followed
- neither version improved resolution or reduced no-edit timeouts

**Does not show:**
- that time awareness can't help. The agent never saw a mid-session time reading, so whether it would act on one is **untested**.
- anything about a harness that *pushes* budget information to the agent every turn, as SWE-Master [4] does. A declarative submission can't add that.
- anything about other models, larger samples, or the dev/hidden task distribution

So this is a failed instruction-compliance mechanism, not a general conclusion about the model's capability or about time awareness.

## 9. Scoring-environment limitations

- `requests_7505` (tests need the `pytest-httpbin` fixture) and `fastapi_14962` (needs `inline_snapshot`) can't pass in our local evaluator.
  It uses swegemma's subprocess sandbox, which skips test-dependency installation (`docs/scoring_environment_comparison.md`).
- In RUN-009 both produced empty patches, so the blockage didn't change any V2 iteration 2 outcome. The exclusion is fixed in advance, not chosen after the fact.
- These are local results from the participant-side evaluator, **not** Kaggle official scores. The official Stage 2 scorer likely has these test packages (not verified).

## 10. Pre-registered indicators

| Indicator | It.1 RUN-008 | It.2 RUN-009 |
|---|---|---|
| ≥ 7/10 tasks make 2+ checks | Not met (0/10) | Not met (0/10) |
| Tasks with no edit by 135 s check after 135 s | — | Not met (0) |
| Halfway compliance (edit after a halfway check) | Not testable (never triggered) | Not testable |
| < 5/10 time out without a successful source-edit tool call | Not met (6) | Not met (7) |
| No more than 1 new turn-cap failure | Met (0) | Met (1) |
| Modest status-check overhead | Met (≈ 2 s per check) | Met (≈ 2 s per check) |
| Resolution reported regardless | 2/10 | 1/10 |

## 11. Why there is no third iteration and no dev run

- **No third iteration:** two designs failed on the same step (getting the agent to check again). The next prompt idea would have weak priors and
  would cost another smoke run. The lever likely to work, a per-turn budget message from the environment, is outside what a declarative submission can do.
- **No dev run:** rule 6 needs a dev score before review, but scoring a mechanism that never activates would spend about 2.5 GPU-hours to measure the
  control prompt plus one opening status check. Dev also stays uncontaminated: V2 was designed and revised on smoke only.
- V2 is therefore **not proposed for review or submission**. It's documented as a failed experiment under rule 7, which counts toward the report.

## 12. Reproducibility

- **Agents:** `git show cfec23d:variants/khushi-anti-looping-v2/...` (iteration 1) and `af977ad` (iteration 2), branch `khushi/anti-looping-v2`.
  Adapter weights are git-ignored: download Kaggle's `sample_submission/adapters/*/adapter_model.safetensors` (sha256 `dcbedd98…`) into the folder.
- **Re-run:** check out the commit, then `python harness/run_kaggle.py variants/khushi-anti-looping-v2 smoke` (same image digest, read live from the official notebook).
- **Raw outputs** stay git-ignored on Khushi's machine (artifact paths above). That includes each run's uploaded agent snapshot, traces, `task_details/` with Phase 2 output, and `run_info.json`.
- **Limitations:**
  - one run per arm
  - the control (RUN-006) wasn't re-run alongside either V2 run
  - temperature 0.2, so outcomes vary between runs
  - check times are trace times, a few seconds ahead of the agent clock
