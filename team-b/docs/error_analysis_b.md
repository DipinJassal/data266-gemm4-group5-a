# Team B error analysis

Owner: Naveen. Draft updated November 24, 2026.

Team B targets failures in localization, patch correctness, verification and patch hygiene. The baseline summary reuses Khushi's published Team A analysis rather than a new baseline run. Direct Team B labeling currently covers only four task executions across the initial and R2 reproduce-first pilots: the same two unique smoke tasks in each pilot. Other Team B findings below remain author-reported summaries; their traces, patches and scoring output have not been independently labeled here. The broader Team B labeling assignment is incomplete.

## Evidence and comparison baseline

The assignment and ownership follow [TEAM_B_PLAN.md](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/f6395a141cc99754c36eff9fbb15dc665dad367f/team-b/TEAM_B_PLAN.md#naveen--testing--verification-error-analysis) and [TEAM_B_GUIDE.md](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/f6395a141cc99754c36eff9fbb15dc665dad367f/team-b/TEAM_B_GUIDE.md). Team A evidence below is pinned to main commit `df49d03a7f987795f38d960b00e2ff983897b9c0`.

| Run | Budget per task | Split | Reported result | Use in this analysis |
|---|---|---|---|---|
| Unmodified sample agent, November 10 | 1 minute / 10 calls | dev, 30 tasks | 2/30 resolved; 1.09 minutes average | Historical baseline and published failure labels |
| Budget-fixed base, November 10 | 4.5 minutes / 50 calls | smoke, 10 tasks | 2/10 resolved; 4.2 minutes average | Earlier reference recorded in Team B's experiment log |
| Budget-fixed control, RUN-006, November 14 | 4.5 minutes / 50 calls | smoke, 10 tasks | 1/10 resolved; 4.67 minutes average | Later control with detailed published smoke analysis |
| Budget-fixed base, run by Ashmitha, logged November 22 | 4.5 minutes / 50 calls | dev, 30 tasks | 7/30 resolved; 3.7 minutes average | New author-reported selection control in PR #6; raw artifacts not independently checked |

Sources: [baseline analysis, sections 1–3](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/df49d03a7f987795f38d960b00e2ff983897b9c0/docs/error_analysis.md), [Team B reference log](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/f6395a141cc99754c36eff9fbb15dc665dad367f/team-b/docs/experiment_log.csv), and [smoke comparison](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/df49d03a7f987795f38d960b00e2ff983897b9c0/docs/v1_smoke_analysis.md).

Every Team B variant starts from `team-b/variants/base`, the budget-fixed agent. The one-minute baseline is therefore historical context, not a matched control for attributing a variant's effect. The two base smoke runs must remain separate: Khushi reports that the earlier run used an older harness revision. The newly reported base dev result is 7/30, not the historical 2/30. Its [PR #6 log entry](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/3f63a05055d2669719ba48d0e81cd07e8dd0ebb4/team-b/docs/experiment_log.csv) records git `6c0aa88`; that PR is not yet merged, and run metadata and artifacts are still needed to verify the comparison. These are participant-harness results, not official Kaggle scores.

## Published baseline failure counts

Khushi assigns one primary patch-outcome label per task and separate contributing flags. Recounting the 30 published task rows reproduces the following totals; the raw run ZIP has not been reanalyzed here.

| Primary outcome | Tasks | Interpretation |
|---|---:|---|
| Empty/invalid diff | 23 | 20 empty patches plus 3 containing only scratch scripts, with no source change |
| Right file, wrong fix or broke other tests | 5 | Source patches overlapping reference files that failed scoring; the two causes cannot be separated |
| Wrong file found | 0 | No final source patch changed only non-reference files; this does not establish correct localization |
| Resolved | 2 | Scoring tests passed |
| Total | 30 | 28 unresolved tasks |

The baseline did not save Phase 2 test output. Do not report five confirmed regressions or five confirmed logic errors. The harness's eight non-empty failing patches comprise the five source patches above and three scratch-only patches.

| Contributing flag | Tasks out of 30 | Meaning |
|---|---:|---|
| T | 28 | Session ended by timeout |
| C | 14 | Reached the tool-call cap |
| G | 12 | Cut off while generating: at least 15 seconds after the last tool result with no further call |
| R | 23 | Read a file more than once, possibly different ranges |
| D | 4 | Repeated the same file and line range exactly |
| M | 8 | Malformed tool-call arguments |
| S | 6 | Scratch script remained in the final patch |
| L | 5 | Never opened a file from the reference patch |
| P | 2 | Edited only part of a multi-file reference fix |
| X | 3 | The agent's reproduction script crashed |

Flags overlap and must not be added to the primary counts. Re-reading different ranges is not sufficient evidence of looping. Reference-file overlap is a localization heuristic: the reference patch is one valid solution, not the only possible solution. Source: [baseline analysis, sections 3–6](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/df49d03a7f987795f38d960b00e2ff983897b9c0/docs/error_analysis.md).

## Failures targeted by Team B

| Owner and variant | Target | Evidence to track in Team B runs |
|---|---|---|
| Ashmitha: `patch-hygiene` | Empty/invalid patches and scratch files | Empty and scratch-only patches separately; scratch files remaining; compilation outcomes |
| Parth: `analyzer-plan` | Poor localization | Analyzer invocation; files examined; time and calls to first source change |
| Parth: `diff-critic` | Wrong or incomplete fixes | Critic invocation; whether feedback caused a revision; subsequent scoring outcome |
| Ishan: `graph-localize`, `graph-expand` | Poor localization and incomplete multi-file coverage | Graph-tool use; localization on train tasks; calls to first source change |
| Naveen: `repro-first` | Weak verification of the reported bug | Issue-related reproduction failure before the fix; same check after the fix; reproduction time and scratch cleanup |
| Naveen: `regression-check` | Newly broken existing behavior | Related existing tests run; evidence of pass before and fail after an edit; source correction and rerun |

These targets come from the agreed plan; the counts do not establish that any proposed intervention works. Confirm general failure patterns on smoke/train before refining variants. Do not use individual dev cases or their reference patches to tune prompts, skills or test selection.

The later matched smoke comparison reinforces two measurement needs. Its control had five tasks with no source change and four patches containing scratch files; only one task ran pytest. The structured-loop treatment made 24 pre-edit reproduction runs versus nine in the control, while both resolved 1/10. This is a warning to measure reproduction cost, not evidence that reproduction necessarily harms performance. Source: [smoke comparison, summary and interpretation](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/df49d03a7f987795f38d960b00e2ff983897b9c0/docs/v1_smoke_analysis.md).

## Labeling future Team B runs

Retain Team A's labels and separate patch outcome, scoring outcome and contributing behavior. Use `unknown` when the evidence cannot distinguish causes.

1. Identify the run by variant commit, split, task IDs, model, sampling, budget and harness revision. Preserve the original run ID and artifact location.
2. Record the harness result and final patch for every task. Distinguish an empty patch, a scratch-only patch and a source patch. A tool call marked successful does not by itself prove a useful final source change; shell commands can also modify source.
3. Assign one primary outcome: resolved; empty/invalid diff; wrong file found; right file/wrong fix; broke other tests; or unknown. Keep wrong fix and regression combined when they are not separable. Establish localization only where permitted evidence supports it; avoid opening dev reference patches for variant design.
4. Record timeout/looping and Team A's other contributing flags separately. Mark environment failures separately from agent failures. Missing packages or fixture errors do not prove that a patch broke working tests. A regression label requires evidence that the affected test previously passed in the same environment.
5. For every nontrivial label, link the exact patch, trace event or test-output excerpt. Missing traces or test output remain missing evidence, not zero events or a passing check.
6. Reconcile one row per expected task, primary totals and harness pass counts before reporting. Keep the full split score as the main result; any exclusion of environment-blocked tasks is a separately labeled sensitivity analysis.

Suggested row fields: `run_id`, `variant_commit`, `split`, `instance_id`, `harness_outcome`, `patch_kind`, `primary_label`, `flags`, `environment_status`, `evidence_path`, `evidence_excerpt`, `review_notes`. Keep raw traces and large logs out of Git; commit small summaries under `team-b/results/`.

Later Team A evaluation identified missing scoring dependencies and fixture errors. Those findings justify an environment flag, not retrospective relabeling of baseline tasks whose scoring output is unavailable. Source: [dev analysis, environment limitations](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/df49d03a7f987795f38d960b00e2ff983897b9c0/docs/v1_dev_analysis.md).

## Team B results and next evidence

The November 21 reproduce-first pilot resolved 1/2 smoke tasks, averaging 4.085 minutes per task. `fastapi_11194` receives primary label empty/invalid diff (scratch-only) with timeout and scratch-file flags; `fastapi_13537` receives resolved. Both loaded the skill, but the failed task exceeded its reproduction limit and never edited source. The passing task's pre-edit assertion failure returned exit code 0, requiring inspection of the actual output. See the [pilot evidence](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/ce8ec2d2cdc8e83a4272492ee071fc768e269794/team-b/results/repro-first-pilot-20261121.md) for exact trace locations and limitations. This is not a full-smoke or dev result.

The [R2 pilot](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/ce8ec2d2cdc8e83a4272492ee071fc768e269794/team-b/results/repro-first-r2-pilot-20261121.md) also resolved 1/2, averaging 4.565 minutes per task. The failed task is now empty/invalid diff (empty), with a timeout and no source edit; the resolved task remains resolved. Its first source edit occurred at 217.6 seconds of the 270-second agent budget. Neither final patch contains scratch scripts, but both traces exceed the revised reproduction-attempt limits. R2 is not a demonstrated improvement. Both pilots are logged separately; further evaluation is pending a design and compute-priority decision.

Ashmitha's [patch-hygiene report](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/3f63a05055d2669719ba48d0e81cd07e8dd0ebb4/team-b/variants/patch-hygiene/README.md) records 1/10 on each smoke iteration and 4/30 on dev against the reported base's 7/30. The variant is not promoted into the combined agent. Those totals are author-reported, not new per-task labels in this analysis. Ishan has offered artifacts for his two ten-task smoke runs; obtaining and labeling those 20 executions is the next way to extend coverage without another GPU run. Official retrieval scores and Poushali's newer evidence are summarized separately in the [verification report](../report/sections/verification.md#comparison-with-other-members-findings).

To add labels, obtain each run's `run_info.json`, `harness_results.jsonl`, final patches or `submission.csv`, traces and available `task_details/` scoring output. Dipin/Khushi's existing budget-fixed smoke/dev artifacts should be reused; do not rerun the base for this analysis. The published baseline ZIP is `baseline-dev-20261110.zip`, held outside Git by Team A.

For Naveen's variants, report reproduction success before/after edits, related-test execution, confirmed regressions, scratch files, timeouts, runtime and resolution on the same task set and harness revision as the control. Describe a failed approach only after measured Team B evidence supports that conclusion. Coordinate the regression-check design with Poushali's test-runner work before evaluation, as required by the Team B plan.
