# Testing and verification

Owner: Naveen. Draft updated November 24, 2026. Local implementation and packaging checks are complete. Initial and R2 pilots each resolved 1/2 of the same two tasks; full-smoke and dev results remain pending. Reproduce-first is in [draft PR #20](https://github.com/DipinJassal/data266-gemm4-group5-a/pull/20); regression-check is a local implementation awaiting coordination and its own PR. Reviewers cannot yet inspect regression-check in GitHub, so its design and local validation below are author-reported, not independently reviewed.

## Research question and baseline

Can an issue-specific reproduction or a targeted regression check improve patch correctness within the existing 4.5-minute budget? The two variants below are independent copies of `team-b/variants/base`, not a sequence of accumulated changes. Both retain the base model, adapters, sampling, analyzer sub-agent and evaluation settings: 4.5 minutes, 50 tool calls, 50 turns and a 60-second command timeout.

The historical one-minute sample-agent run resolved 2/30 dev tasks. Khushi's published labels identify 23 tasks with no source change, five failed source patches whose wrong-fix/regression causes cannot be separated, and two resolves. These counts motivate what to measure, not a claim that either new variant improves results. The budget-fixed base is the appropriate control for attribution. Ashmitha now reports 7/30 dev at 3.7 minutes per task in [PR #6's log](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/3f63a05055d2669719ba48d0e81cd07e8dd0ebb4/team-b/docs/experiment_log.csv); raw artifacts and matched-run provenance have not been independently checked, and that PR remains unmerged. See [Team B error analysis](../../docs/error_analysis_b.md) for sources, definitions and separate run identities.

## V1 Reproduce first

`team-b/variants/repro-first/` registers `skills/reproduce-first` in `agent.yaml`. The root prompt explicitly calls `load_skill` before the first source edit and requires its post-edit check and scratch cleanup before submission.

The initial skill used a temporary Python assertion with bounded corrections and cleanup. After its scratch-only timeout, R2 requested inline Python with uncaught assertions and no scratch scripts: one pre-edit execution, then one identical post-edit execution only after confirmed reproduction. Blocked or already-passing checks should lead directly to the source fix. These instructions were not consistently followed in either pilot.

This is one verification intervention expressed through the skill and its invocation points. No model, sampling or runtime-budget change is included. It follows the Team B plan's V1 assignment and assigned references [3] and [12]. Skill registration and loading follow the competition's `HARNESS_README.md` and the [ADK skill format](https://github.com/google/adk-docs/blob/main/docs/skills/index.md).

**Hypothesis:** a stable before/after check may reduce wrong fixes. **Risk:** script generation or repair may delay the first source edit, and a passing local assertion may miss behavior checked by the scorer. Measure skill loading, actual issue reproduction, before/after outcomes, reproduction executions, time to first edit, scratch files remaining and resolution. These behaviors are prompt instructions; offline validation does not prove the agent will follow them.

## V2 Targeted regression check

`team-b/variants/regression-check/` changes only the root prompt, apart from its README. It selects a directly related existing test file for each changed source module, deduplicates selections, and runs `pytest -q -x --tb=short <test_file>` with a focused selection if necessary. It records an initial result and reruns the same checks after editing. The initial result is needed to distinguish a new failure from one already present.

A newly failing test that previously passed can trigger one source-only correction and an affected-test rerun. Tests and assertions are never modified. Unexecuted tests after an early `-x` failure remain unknown; missing dependencies, setup errors and timeouts are recorded as blocked checks. If a newly changed module lacks a pre-edit result, its regression status is also unknown. Checks already run on the final source state are not repeated merely to satisfy the checklist.

This follows the Team B plan's V2 assignment and assigned reference [4]. The base already asks for a targeted check; the added intervention is explicit coverage of changed modules and comparison with their pre-edit test outcomes. **Hypothesis:** this may catch newly broken existing behavior. **Risk:** running tests twice consumes time and may encounter environment failures unrelated to the patch.

Poushali's [test-runner implementation](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/8718aaaca81c752760ec9965723e108e60ffe0c2/variants/poushali-test-runner-v2/prompts/test_runner.md) delegates post-edit test discovery and execution to a sub-agent. This draft keeps verification in the root agent and adds a before/after comparison to distinguish newly introduced regressions. Coordination with Poushali remains pending; this is a proposed distinction, not an agreed comparison. V2 evaluation is on hold until coordination is resolved.

## Evaluation status and method

| Check or result | Reproduce first | Regression check |
|---|---|---|
| Source base | `f6395a1`, Team B base | Same base independently copied |
| Unchanged inherited configuration | Verified against GitHub blob hashes | Verified against GitHub blob hashes |
| Repository offline validator | Passed | Passed |
| Skill metadata | Name, description, directory and registration checked | Not applicable |
| Submission ZIP | Passed integrity checks; 12 files, `agent.yaml` at root | Passed integrity checks; 11 files, `agent.yaml` at root |
| Participant evaluator on Kaggle | Both pilots ran both tasks; skill loaded in all four task executions | Pending |
| Two-task smoke pilots | Initial: 1/2 at 4.085 min/task. R2: 1/2 at 4.565 min/task. One timeout each; R2 empty patch replaced the scratch-only failure. | Pending coordination and execution |
| Full smoke, 10 tasks | Pending | Pending coordination and execution |
| Final dev, 30 tasks | Pending | Pending |
| Official Kaggle result | Pending | Pending |

ZIP checks used official sample adapter weights in local staging. Weights and ZIPs are excluded from source deliverables. Local validation establishes packaging consistency; it does not establish runtime skill loading, instruction compliance, correctness or score.

Start with a two-task smoke pilot, then the full smoke split. Preserve the pilot before reusing its kernel for a full run. Inspect crashes, task completeness, verification behavior and average task time below approximately six minutes. Tune only on smoke/train. Freeze each candidate before its single final dev run, and record actual outcomes beside the matched base in the experiment log. A later change creates a new candidate. Label dev as validation used for selection and the official Kaggle result as held-out evaluation.

Use the same task IDs, harness revision, environment, model and budgets in a matched comparison. Keep full-split scores as the main result. Missing dependencies and other environment limitations should be separately labeled; any sensitivity analysis excluding blocked tasks must not replace the full score. Use [the shared label method](../../docs/error_analysis_b.md#labeling-future-team-b-runs) and preserve per-task traces, final patches and test output for review.

## Results and failed approaches

The [reproduce-first pilot](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/ce8ec2d2cdc8e83a4272492ee071fc768e269794/team-b/results/repro-first-pilot-20261121.md) supplies a concrete failure case. One task loaded the skill but generated three reproduction scripts, exceeded the two-execution pre-edit limit, timed out without a source edit, and left all three scripts in the scored patch. The other task reproduced an assertion failure, fixed source, passed its check and scoring tests, and removed its scratch script. However, its pre-edit failing assertion printed a traceback while returning exit code 0. Loading the instructions therefore did not guarantee the intended bounded, reliable verification behavior.

The [R2 pilot](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/ce8ec2d2cdc8e83a4272492ee071fc768e269794/team-b/results/repro-first-r2-pilot-20261121.md) also resolved 1/2, averaging 4.565 minutes per task rather than 4.085. No scratch scripts remained, but the same failed task timed out with an empty patch. It made five pre-edit reproduction attempts; the resolved task made four pre-edit and three post-edit attempts. The resolved task showed a nonzero issue-related failure and a later passing check, but changed its check and encountered quoting/syntax errors. R2 is not a demonstrated improvement. Both iterations provide failure evidence for prompt-based attempt limits. Further evaluation is pending a design and compute-priority decision. Two tasks without a matched base control establish neither general improvement nor general ineffectiveness.

Time to first source edit makes the cost concrete: R2's resolved task, `fastapi_13537`, first edited source at **217.6 seconds of a 270-second budget**, leaving 52.4 seconds of nominal agent time. The failed task, `fastapi_11194`, never edited source. This is observed timing, not proof that reproduction alone caused the delay.

| Reproduce-first pilot | Resolved | Mean task time | Timeout | Empty patch | Scratch-only patch |
|---|---:|---:|---:|---:|---:|
| Initial | 1/2 | 4.085 min | 1 | 0 | 1 |
| R2 | 1/2 | 4.565 min | 1 | 1 | 0 |

### Comparison with other members' findings

Ishan's [merged retrieval report](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/e13ba96f7b0ce5d722c536233da28c742340db23/team-b/report/sections/retrieval.md) reports 1/10 smoke for both evaluated graph variants and source edits in only 3/10 tasks per variant. The [log merged through PR #26](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/96b0a25cb01e8b256d9e1e94069b160fd81689b4/team-b/docs/experiment_log.csv) now records public Kaggle scores of **0.12 for graph-localize** and **0.08 for graph-expand-2**, one submission each. The newer [base score entry in PR #6](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/ab8fa0a888e05f48c4e285786851a3d972d74664/team-b/docs/experiment_log.csv) records **0.10** for Team B's base (submission ref **58768806**). The graph variants are therefore +0.02 and -0.02 against the base, respectively. With one submission per candidate, these small differences do not establish a reliable improvement or deterioration. These official scores must remain separate from local smoke/dev fractions.

Ashmitha's [patch-hygiene report](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/3f63a05055d2669719ba48d0e81cd07e8dd0ebb4/team-b/variants/patch-hygiene/README.md) records **4/30 dev against base 7/30** and a decision not to promote the variant. Its per-task traces and run metadata have not been independently analyzed here; preserving the negative result is useful, but the result is not proof that every hygiene intervention is ineffective.

Poushali's [skills-pack smoke analysis](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/1f57c1d0d859b6c122e9ece236096194584f7eed/docs/skills_pack_v1_analysis.md) reports 1/10 despite loading the skill in all ten tasks, with 22 pre-edit Python runs versus nine in RUN-006. The newer [dev result rows in PR #27](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/2b6e2b0f3ef441728be6fd061293a117650a71c9/docs/runs/poushali-skills-pack-v1-dev-20261123T191033Z/harness_results.jsonl) independently recount to **6/30 resolved**, five empty patches, 19 non-empty unresolved patches and 3.981 minutes mean task time. The errors include 19 session timeouts and one context-window crash. This verifies summary totals, not new trace-based labels or comparison with Team B's base. [Run metadata](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/2b6e2b0f3ef441728be6fd061293a117650a71c9/docs/runs/poushali-skills-pack-v1-dev-20261123T191033Z/run_info.json) records a dirty working tree; full traces and the exact uploaded configuration are not independently verified here. The merged implementation is in [PR #22](https://github.com/DipinJassal/data266-gemm4-group5-a/pull/22); an official Kaggle score is not available in the reviewed evidence.

Her [updated test-runner analysis](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/bd2756568535b90b43c33c8d55a037df18f3f5a0/docs/test_runner_v2_analysis.md) reports 2/10 and 1/10, with the sub-agent invoked in zero and one tasks respectively. It now includes raw summary files and records one context-window crash in the second run; it should not be described as crash-free. Detailed behavior counts remain author-reported without a full trace reanalysis here. These findings support measuring edit timing and instruction compliance, but do not establish a common cause or justify ranking variants from unmatched runs.

### Next work and limits

[Ishan's review](https://github.com/DipinJassal/data266-gemm4-group5-a/pull/20#pullrequestreview-6009156735) proposes editing before verification, shortening the skill, and checking remaining time. These are untested proposals for this variant. Poushali already reports difficulties with edit-early instructions and post-edit tool triggers, so another wording revision is not assumed to help. Preserve both candidates and obtain a reviewable comparison plan before spending further quota. Full smoke, final dev, official submission, and the coordinated regression-check experiment remain incomplete.

Evidence links above are pinned to commits so this documentation remains readable before PR #20 merges. Detailed reports record ZIP hashes and provenance. Raw private run artifacts are retained by Naveen and can be shared with reviewers; their local storage paths are not public downloads.

The completed local work uncovered an infrastructure issue: Kaggle CLI 1.7.4.5 rejects `--accelerator` and does not forward `machine_shape` from metadata. [Parth's updated launcher in PR #15](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/237be280e348689e2d1337e8e17c1ce175769112/team-b/kaggle/run_kaggle.py) now requires CLI 2.x and pins the Python 3.12 runtime; its latest revision also adds a guard against stale input uploads. [PR #15](https://github.com/DipinJassal/data266-gemm4-group5-a/pull/15) is merged into `group5-team-b`. Use and validate the agreed launcher/runtime before a future run; this update does not retroactively verify either pilot's runtime image or imply a new run occurred.
