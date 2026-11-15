# Experiment-log entries for RUN-008 and RUN-009 (pending workbook integration)

*Khushi, Nov 15. `docs/experiment_log.xlsx` is deliberately **not** edited in this change. Sarvesh's PR #5 carries its own copy of the workbook, which
conflicts with `main` (binary add/add conflict). These rows are ready to paste once that's resolved. Every value is verified from raw run outputs;
details are in `docs/v2_time_awareness_analysis.md`.*

## Run Details sheet (same 19 columns, same conventions as RUN-005/RUN-006)

"Wrong patches" = non-empty patches that didn't resolve, as in the existing rows. "Resolved %" uses the sheet's own formula.

| Column | RUN-008 | RUN-009 |
|---|---|---|
| Run ID | RUN-008 | RUN-009 |
| Run date | 2026-11-15 (05:19–06:14 UTC) | 2026-11-15 (18:39–19:31 UTC) |
| Variant | khushi-anti-looping-v2 (iteration 1) | khushi-anti-looping-v2 (iteration 2) |
| Run by | Khushi Donda | Khushi Donda |
| Split | smoke | smoke |
| Tasks tested | 10 | 10 |
| Tasks resolved | 2 | 1 |
| Resolved % | (formula) | (formula) |
| Empty patches | 4 | 5 |
| Wrong patches | 4 | 4 |
| Avg min/task | 4.49 | 4.31 |
| Max min/task | 5.17 | 4.65 |
| Tool calls (avg) | 19.8 | 21.7 |
| Time limit (min) | 4.5 | 4.5 |
| Tool call cap | 50 | 50 |
| Evidence status | Verified from run outputs (Nov 15); Phase 2 output captured | Verified from run outputs (Nov 15); Phase 2 output captured |
| Local artifact / trace | harness/runs/variants-khushi-anti-looping-v2/smoke/20261115T065200Z (git-ignored); evaluated folder now commit cfec23d (byte-identical; run recorded base a6c709d + uncommitted folder); system.md sha256 03d1e909…; 4x L4; Khushi's quota; genuine sample adapters dcbedd98… (git-ignored) | harness/runs/variants-khushi-anti-looping-v2/smoke/20261115T193206Z (git-ignored); commit af977ad; system.md sha256 53662ae1…; 4x L4; Khushi's quota; genuine sample adapters dcbedd98… (git-ignored) |
| Source URL | local run outputs (not in repo) | local run outputs (not in repo) |
| Notes / interpretation | Time-budget prompt, iteration 1 ("get_status() first, then every 8 tool calls"). First-action check 7/10; 0/10 tasks checked again, so the halfway/endgame rules never fired. Resolved fastapi_11194 and fastapi_13537. 6/10 timed out with no successful source-edit tool call (control RUN-006: 5). Patches 4 source / 2 scratch-only / 4 empty; 0 turn-cap, 0 context errors. requests_7505 source patch unscoreable (httpbin). Exploratory; 2/10 not attributable to the mechanism. | Iteration 2: event trigger ("before every run_command until a source edit"). First-action check 10/10; 0/10 checked again. Resolved fastapi_13537. 7/10 timed out with no successful source-edit tool call (6 if counting any source-tree change: fastapi_14609 deleted 3 source files via rm at 268 s, breaking collection). Patches 2 source / 1 deletion-only / 2 scratch-only / 5 empty; 1 turn-cap (rich_4075, 50 turns at 269 s); 0 context errors. V2 closed as a negative result; no dev run. |

## Experiment Log sheet: replace the planned `khushi-anti-loop-v2` row (row 10 on `main`)

The planned row uses a placeholder name and description. The folder that was built and evaluated is `khushi-anti-looping-v2`, a time-awareness prompt.

| Column | Proposed value |
|---|---|
| Variant | khushi-anti-looping-v2 |
| Owner | Khushi Donda |
| One-line change | Time-budget section in system prompt: check get_status() and switch to editing at the halfway point (prompt only) |
| Smoke time (min/task) | Formula pointing at RUN-009's "Avg min/task" cell (4.31) |
| Dev score | (blank; no dev run) |
| Kaggle score | (blank) |
| Status | Smoke-tested; closed (negative result) |
| Notes | Two smoke iterations vs control RUN-006 (1/10): it.1 RUN-008 2/10, it.2 RUN-009 1/10. Neither made a second status check in any task (0/10 both), so the halfway/endgame rules never fired; no reliable improvement. Not proposed for review or submission. Details: docs/v2_time_awareness_analysis.md. |
| Comparator / parent | dipin-step-budget-v1 (provisional control; pending team confirmation; rule 1 unchanged) |
| Reviewer | Sarvesh |
| Evidence | Smoke runs verified from raw run outputs |
| Source URL | https://github.com/DipinJassal/data266-gemm4-group5-a/blob/main/docs/v2_time_awareness_analysis.md (after merge) |

## Integration plan (once the workbook is safe to edit)

The PR #5 workbook differs from the version merged in PR #1 in exactly 24 cells:
- 17 cells: one Run Details row, RUN-S01, at row 10
- 7 cells: the `sarvesh-sampling-v1` Experiment Log row, row 11

On `main`, Run Details row 10 is now RUN-004, so the PR #5 file can't simply replace `main`'s: that would delete RUN-004 to RUN-007 and the V1 rows.

To integrate without losing anything:
1. Start from `main`'s workbook (RUN-001 to RUN-007, three labelling sheets).
2. Append RUN-S01 at the next free Run Details row (row 14), with Sarvesh's 17 values unchanged.
3. Apply his 7 cell values to `main`'s `sarvesh-sampling-v1` row (row 11).
4. Append RUN-008 (row 15) and RUN-009 (row 16) from the tables above.
5. Replace the `khushi-anti-loop-v2` row with the values above.
6. Update START HERE B20 (the count of documented runs). The RUNS DOCUMENTED counter is a formula and updates itself.
7. Re-save with the chart-preserving procedure used for PR #9 (openpyxl drops the LibreOffice chart series otherwise).

Run IDs: RUN-S01 keeps Sarvesh's ID. RUN-008 and RUN-009 continue the RUN-00x sequence and don't collide with it.
