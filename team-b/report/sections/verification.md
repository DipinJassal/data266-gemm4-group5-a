# Testing and verification

Owner: Naveen. Updated November 25, 2026. Reproduce-first remains in [draft PR #20](https://github.com/DipinJassal/data266-gemm4-group5-a/pull/20): initial and R2 pilots each resolved 1/2 of the same two tasks. The separately evaluated edit-early variant resolved 5/30 dev tasks against the reported base 7/30 and was merged as experiment evidence in [PR #31](https://github.com/DipinJassal/data266-gemm4-group5-a/pull/31), without promotion. Coordination with Poushali is complete. Regression-check remains a local, unevaluated implementation; its design and offline checks below are author-reported and are not inspectable in GitHub. Further experiments are deferred under the team's current hold on new cap or prompt-only variants.

## Research question and baseline

Can an issue-specific reproduction or a targeted regression check improve patch correctness within the existing 4.5-minute budget? The two variants below are independent copies of `team-b/variants/base`, not a sequence of accumulated changes. Both retain the base model, adapters, sampling, analyzer sub-agent and evaluation settings: 4.5 minutes, 50 tool calls, 50 turns and a 60-second command timeout.

The historical one-minute sample-agent run resolved 2/30 dev tasks. Khushi's published labels identify 23 tasks with no source change, five failed source patches whose wrong-fix/regression causes cannot be separated, and two resolves. These counts motivate what to measure, not a claim that either new variant improves results. The budget-fixed base is the appropriate control for attribution. Ashmitha now reports 7/30 dev at 3.7 minutes per task in [PR #6's log](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/3f63a05055d2669719ba48d0e81cd07e8dd0ebb4/team-b/docs/experiment_log.csv); raw artifacts and matched-run provenance have not been independently checked, and the log is now part of the Team B integration branch. See [Team B error analysis](../../docs/error_analysis_b.md) for sources, definitions and separate run identities.

## V1 Reproduce first

`team-b/variants/repro-first/` registers `skills/reproduce-first` in `agent.yaml`. The root prompt explicitly calls `load_skill` before the first source edit and requires its post-edit check and scratch cleanup before submission.

The initial skill used a temporary Python assertion with bounded corrections and cleanup. After its scratch-only timeout, R2 requested inline Python with uncaught assertions and no scratch scripts: one pre-edit execution, then one identical post-edit execution only after confirmed reproduction. Blocked or already-passing checks should lead directly to the source fix. These instructions were not consistently followed in either pilot.

This is one verification intervention expressed through the skill and its invocation points. No model, sampling or runtime-budget change is included. It follows the Team B plan's V1 assignment and assigned references [3] and [12]. Skill registration and loading follow the competition's `HARNESS_README.md` and the [ADK skill format](https://github.com/google/adk-docs/blob/main/docs/skills/index.md).

**Hypothesis:** a stable before/after check may reduce wrong fixes. **Risk:** script generation or repair may delay the first source edit, and a passing local assertion may miss behavior checked by the scorer. Measure skill loading, actual issue reproduction, before/after outcomes, reproduction executions, time to first edit, scratch files remaining and resolution. These behaviors are prompt instructions; offline validation does not prove the agent will follow them.

## V2 Targeted regression check

`team-b/variants/regression-check/` changes only the root prompt, apart from its README. It selects a directly related existing test file for each changed source module, deduplicates selections, and runs `pytest -q -x --tb=short <test_file>` with a focused selection if necessary. It records an initial result and reruns the same checks after editing. The initial result is needed to distinguish a new failure from one already present.

A newly failing test that previously passed can trigger one source-only correction and an affected-test rerun. Tests and assertions are never modified. Unexecuted tests after an early `-x` failure remain unknown; missing dependencies, setup errors and timeouts are recorded as blocked checks. If a newly changed module lacks a pre-edit result, its regression status is also unknown. Checks already run on the final source state are not repeated merely to satisfy the checklist.

This follows the Team B plan's V2 assignment and assigned reference [4]. The base already asks for a targeted check; the added intervention is explicit coverage of changed modules and comparison with their pre-edit test outcomes. **Hypothesis:** this may catch newly broken existing behavior. **Risk:** running tests twice consumes time and may encounter environment failures unrelated to the patch.

Poushali's [test-runner implementation](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/8718aaaca81c752760ec9965723e108e60ffe0c2/variants/poushali-test-runner-v2/prompts/test_runner.md) delegates post-edit test discovery and execution to a sub-agent. This draft keeps verification in the root agent and adds a before/after comparison to distinguish newly introduced regressions. Poushali confirmed that this comparison is appropriate. Her recommendations are to record whether tests actually execute before and after editing, place the final test trigger before `submit_patch`, keep output short, and distinguish missing dependencies from patch failures. The local coordinated design uses bounded output while preserving the test exit status. Coordination is complete; evaluation remains deferred under the current team priorities. Her confirmation is design feedback, not runtime validation of this variant.

## Evaluation status and method

| Check or result | Reproduce first | Regression check |
|---|---|---|
| Source base | `f6395a1`, Team B base | Same base independently copied |
| Unchanged inherited configuration | Verified against GitHub blob hashes | Verified against GitHub blob hashes |
| Repository offline validator | Passed | Passed |
| Skill metadata | Name, description, directory and registration checked | Not applicable |
| Submission ZIP | Passed integrity checks; 12 files, `agent.yaml` at root | Passed integrity checks; 11 files, `agent.yaml` at root |
| Participant evaluator on Kaggle | Both pilots ran both tasks; skill loaded in all four task executions | Pending |
| Two-task smoke pilots | Initial: 1/2 at 4.085 min/task. R2: 1/2 at 4.565 min/task. One timeout each; R2 empty patch replaced the scratch-only failure. | Not run; deferred |
| Full smoke, 10 tasks | Not run; deferred | Not run; deferred |
| Final dev, 30 tasks | Pending | Pending |
| Official Kaggle result | Pending | Pending |

ZIP checks used official sample adapter weights in local staging. Weights and ZIPs are excluded from source deliverables. Local validation establishes packaging consistency; it does not establish runtime skill loading, instruction compliance, correctness or score.

For a future team-authorized experiment, start with a two-task smoke pilot, then the full smoke split. Preserve the pilot before reusing its kernel for a full run. Inspect crashes, task completeness, verification behavior and average task time below approximately six minutes. Tune only on smoke/train. Freeze each candidate before its single final dev run, and record actual outcomes beside the matched base in the experiment log. A later change creates a new candidate. Label dev as validation used for selection and the official Kaggle result as held-out evaluation.

Use the same task IDs, harness revision, environment, model and budgets in a matched comparison. Keep full-split scores as the main result. Missing dependencies and other environment limitations should be separately labeled; any sensitivity analysis excluding blocked tasks must not replace the full score. Use [the shared label method](../../docs/error_analysis_b.md#labeling-future-team-b-runs) and preserve per-task traces, final patches and test output for review.

## Results and failed approaches

The [reproduce-first pilot](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/ce8ec2d2cdc8e83a4272492ee071fc768e269794/team-b/results/repro-first-pilot-20261121.md) supplies a concrete failure case. One task loaded the skill but generated three reproduction scripts, exceeded the two-execution pre-edit limit, timed out without a source edit, and left all three scripts in the scored patch. The other task reproduced an assertion failure, fixed source, passed its check and scoring tests, and removed its scratch script. However, its pre-edit failing assertion printed a traceback while returning exit code 0. Loading the instructions therefore did not guarantee the intended bounded, reliable verification behavior.

The [R2 pilot](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/ce8ec2d2cdc8e83a4272492ee071fc768e269794/team-b/results/repro-first-r2-pilot-20261121.md) also resolved 1/2, averaging 4.565 minutes per task rather than 4.085. No scratch scripts remained, but the same failed task timed out with an empty patch. It made five pre-edit reproduction attempts; the resolved task made four pre-edit and three post-edit attempts. The resolved task showed a nonzero issue-related failure and a later passing check, but changed its check and encountered quoting/syntax errors. R2 is not a demonstrated improvement. Both iterations provide failure evidence for prompt-based attempt limits. Further evaluation is pending a design and compute-priority decision. Two tasks without a matched base control establish neither general improvement nor general ineffectiveness.

Time to first source edit makes the cost concrete: R2's resolved task, `fastapi_13537`, first edited source at **217.6 seconds of a 270-second budget**, leaving 52.4 seconds of nominal agent time. The failed task, `fastapi_11194`, never edited source. This is observed timing, not proof that reproduction alone caused the delay.

| Reproduce-first pilot | Resolved | Mean task time | Timeout | Empty patch | Scratch-only patch |
|---|---:|---:|---:|---:|---:|
| Initial | 1/2 | 4.085 min | 1 | 0 | 1 |
| R2 | 1/2 | 4.565 min | 1 | 1 | 0 |

### Edit-early: completed follow-up experiment

At the team lead's request, edit-early tested a shorter root prompt: make the first source edit within five tool calls, run targeted tests at most twice, and avoid rereading files. It independently copies base; only the root prompt changes at runtime. Model, adapters, sampling, analyzer and the 4.5-minute / 50-call / 50-turn budget remain unchanged. This is a separate prompt experiment, not an evaluated revision of the reproduce-first skill or regression-check design.

The frozen candidate was `9824af2` (clean working tree), evaluated once on the 30-task dev split on Kaggle L4 x4. The [result summary](../../results/edit-early-dev-20261125.md) and [per-task evidence](../../results/edit-early-dev-20261125.json) record provenance and the independently recounted task outcomes. Source and evidence were merged through PR #31; no official submission was made.

| Dev result | Edit-early |
|---|---:|
| Resolved | 5/30 (16.7%); reported base 7/30 |
| Session timeouts | 18 |
| Turns-budget exhaustion | 1 |
| Empty patches | 6 |
| Context-window errors | 0 |
| Mean task time | 4.0665 min (`duration_seconds` / 60) |

The five passes were `fastapi_14077`, `fastapi_14301`, `fastapi_14492`, `rich_3063` and `rich_3905`. Compared with the team's reported base pass list, edit-early lost `rich_3278` and `rich_3718` and added no passes. Both lost tasks timed out with empty patches and no source edit. The base's raw run was not independently recounted here, so this comparison uses the team's published control results.

Trace inspection found successful implementation edits within the first five recorded tool requests in only 6/30 tasks; 22/30 eventually made one. Repeated reads of a previously read path occurred in 28/30, including reads of different line ranges. Explicit pytest commands appeared in 9/30; this does not measure every form of verification or establish compliance with the two-test limit. Trace request ordinals differ from harness tool counts on 13 tasks and must not be treated as interchangeable.

Edit-early did not meet the team's >=7/30 submission threshold and was not promoted. Shortening the prompt did not ensure that the model followed its early-edit instructions. One dev run does not establish a general causal effect; dev was used for selection, and no further edits or repeat runs were made to chase its score.

### Comparison with other members' findings

Ishan's [merged retrieval report](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/e13ba96f7b0ce5d722c536233da28c742340db23/team-b/report/sections/retrieval.md) reports 1/10 smoke for both evaluated graph variants and source edits in only 3/10 tasks per variant. The [log merged through PR #26](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/96b0a25cb01e8b256d9e1e94069b160fd81689b4/team-b/docs/experiment_log.csv) now records public Kaggle scores of **0.12 for graph-localize** and **0.08 for graph-expand-2**, one submission each. The newer [base score entry in PR #6](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/ab8fa0a888e05f48c4e285786851a3d972d74664/team-b/docs/experiment_log.csv) records **0.10** for Team B's base (submission ref **58768806**). The graph variants are therefore +0.02 and -0.02 against the base, respectively. With one submission per candidate, these small differences do not establish a reliable improvement or deterioration. These official scores must remain separate from local smoke/dev fractions.

Ashmitha's [patch-hygiene report](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/3f63a05055d2669719ba48d0e81cd07e8dd0ebb4/team-b/variants/patch-hygiene/README.md) records **4/30 dev against base 7/30** and a decision not to promote the variant. Its per-task traces and run metadata have not been independently analyzed here; preserving the negative result is useful, but the result is not proof that every hygiene intervention is ineffective.

Poushali's [skills-pack smoke analysis](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/1f57c1d0d859b6c122e9ece236096194584f7eed/docs/skills_pack_v1_analysis.md) reports 1/10 despite loading the skill in all ten tasks, with 22 pre-edit Python runs versus nine in RUN-006. The newer [dev result rows in PR #27](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/2b6e2b0f3ef441728be6fd061293a117650a71c9/docs/runs/poushali-skills-pack-v1-dev-20261123T191033Z/harness_results.jsonl) independently recount to **6/30 resolved**, five empty patches, 19 non-empty unresolved patches and 3.981 minutes mean task time. The errors include 19 session timeouts and one context-window crash. This verifies summary totals, not new trace-based labels or comparison with Team B's base. [Run metadata](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/2b6e2b0f3ef441728be6fd061293a117650a71c9/docs/runs/poushali-skills-pack-v1-dev-20261123T191033Z/run_info.json) records a dirty working tree; full traces and the exact uploaded configuration are not independently verified here. The merged implementation is in [PR #22](https://github.com/DipinJassal/data266-gemm4-group5-a/pull/22); an official Kaggle score is not available in the reviewed evidence.

Her [updated test-runner analysis](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/bd2756568535b90b43c33c8d55a037df18f3f5a0/docs/test_runner_v2_analysis.md) reports 2/10 and 1/10, with the sub-agent invoked in zero and one tasks respectively. It now includes raw summary files and records one context-window crash in the second run; it should not be described as crash-free. Detailed behavior counts remain author-reported without a full trace reanalysis here. These findings support measuring edit timing and instruction compliance, but do not establish a common cause or justify ranking variants from unmatched runs.

### Next work and limits

[Ishan's review](https://github.com/DipinJassal/data266-gemm4-group5-a/pull/20#pullrequestreview-6009156735) proposes editing before verification, shortening the skill, and checking remaining time. These changes have not been evaluated in the reproduce-first skill. The separately completed edit-early experiment above tested an earlier-edit prompt and did not beat base. Reproduce-first was rebased at `8ab19ce` with evaluated files unchanged and both pilot rows preserved; re-review is pending. Its full smoke/dev and official submission remain incomplete. Regression-check coordination is complete, but its execution remains deferred. The remaining analysis of Ishan's 20 smoke traces can label timeouts, empty patches and scratch-only patches; missing per-task test output prevents reliable separation of wrong fixes from regressions.

Evidence links above are pinned to commits so this documentation remains readable before PR #20 merges. Detailed reports record ZIP hashes and provenance. Raw private run artifacts are retained by Naveen and can be shared with reviewers; their local storage paths are not public downloads.

The completed local work uncovered an infrastructure issue: Kaggle CLI 1.7.4.5 rejects `--accelerator` and does not forward `machine_shape` from metadata. [Parth's updated launcher in PR #15](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/237be280e348689e2d1337e8e17c1ce175769112/team-b/kaggle/run_kaggle.py) now requires CLI 2.x and pins the Python 3.12 runtime; its latest revision also adds a guard against stale input uploads. [PR #15](https://github.com/DipinJassal/data266-gemm4-group5-a/pull/15) is merged into `group5-team-b`. Use and validate the agreed launcher/runtime before a future run; this update does not retroactively verify either pilot's runtime image or imply a new run occurred.
