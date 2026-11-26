# Testing, verification and edit timing

Naveen | Team B | One presentation slide | Updated November 25, 2026

**Question:** Can explicit verification or an earlier source edit improve patches within 270 seconds?

| Experiment | Resolved | Min/task | Empty patches |
|---|---:|---:|---:|
| Reproduce-first initial pilot | 1/2 | 4.085 | 0 (one scratch-only patch) |
| Reproduce-first R2 pilot | 1/2 | 4.565 | 1 |
| Edit-early dev | 5/30 | 4.0665 | 6 |

- **Reproduce-first:** R2 removed scratch scripts without a resolution gain. Its solved task first edited source at 217.6/270 seconds; the failed task never edited.
- **Edit-early:** 18 session timeouts; no new passes over reported base 7/30. Only 6/30 edited implementation within five recorded tool requests. Not promoted.
- **Regression-check:** local before/after targeted-test design; Poushali coordination completed. Unevaluated and deferred.

**Takeaway:** Verification and early-edit instructions were not reliably followed. Preserve time for a source fix and measure actual behavior, not just prompt wording.

Speaker note: Pilots are four executions of the same two unique tasks, without a matched base pilot. Dev is validation used for selection; the base's 7/30 and pass list are team-reported. Do not compare pilot fractions directly with the dev score. Trace request ordinals are not identical to harness tool counts. Edit-early's source and evidence merged through PR #31; no official submission or performance gain is claimed. New GPU experiments are deferred under current team priorities.

Sources: [verification section](../report/sections/verification.md), [edit-early results](../results/edit-early-dev-20261125.md), [per-task evidence](../results/edit-early-dev-20261125.json), and [error analysis](../docs/error_analysis_b.md).
