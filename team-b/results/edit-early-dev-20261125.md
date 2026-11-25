# Edit early dev result

The frozen edit-early candidate resolved **5/30 dev tasks (16.7%)**, below Team B's reported base **7/30 (23.3%)**. All five passes were base passes; no new task was solved. Under Ashmitha's at-least-7/30 rule, this candidate is **not selected for official submission**. This is a single validation run, not proof that shortening prompts generally harms performance.

| Metric | Edit early |
|---|---:|
| Unique dev tasks, matching the shared split | 30 |
| Resolved | 5 |
| Session timeouts | 18 |
| Turns-budget exhaustion | 1 |
| Empty patches | 6 |
| Context-window errors | 0 |
| Mean task duration | 4.0665 minutes |

Retained base passes: `fastapi_14077`, `fastapi_14301`, `fastapi_14492`, `rich_3063`, `rich_3905`.
Lost base passes: `rich_3278`, `rich_3718`.
New passes: none.

The base pass set comes from Ashmitha's update and [PR #6's log](https://github.com/DipinJassal/data266-gemm4-group5-a/blob/ab8fa0a888e05f48c4e285786851a3d972d74664/team-b/docs/experiment_log.csv); the base's raw run has not been independently re-counted here. The edit-early totals were independently computed from all 30 `harness_results.jsonl` rows and agree with `run_info.json`.

## Instruction execution

Only **6/30 tasks** showed a successful implementation edit within the first five recorded tool requests; **22/30** showed a successful implementation edit at some point. **28/30** called `read_file` repeatedly on at least one path. This includes different line ranges, so it is not a count of identical rereads. Explicit pytest command calls appeared in **9/30** tasks; this does not count every possible inline/custom verification or prove compliance with the two-test limit.

Both lost base tasks timed out with empty patches and no observed source edit. `rich_3278` made three read calls on `rich/ansi.py`; `rich_3718` made ten tool requests, including repeated reads of `rich/panel.py` and `rich/text.py`. The intended change in behavior was therefore not reliably achieved.

Method: count top-level `tool_calls` entries only, avoiding duplicate observation metadata. A source edit requires a successful `edit_file`/`write_file` response in an implementation directory, including executable documentation examples; root scratch scripts, tests and failed calls are excluded. Request ordinals include failed requests and differ from the harness's counted tool calls on 13 tasks. The six early-edit tasks are `fastapi_14492`, `fastapi_15588`, `requests_7433`, `rich_3052`, `rich_3905` and `rich_4070`. Do not equate tool-request count with elapsed time or claim the prompt caused every failure.

## Provenance

- Notebook: [edit-early dev](https://www.kaggle.com/code/aravapallinaveen05/g5b-eval-team-b-variants-edit-early-dev), launched as version 1.
- Run metadata: git revision `9824af2`, `dirty: false`; dev split; 4 NVIDIA L4 GPUs; Python 3.12.13.
- Budgets: 4.5 minutes, 50 tool calls, 50 turns; 60-second command timeout.
- Start: 2026-11-25 09:04:57 UTC (01:04:57 Pacific). Finish: 11:16:39 UTC (03:16:39 Pacific).
- Runtime image: `gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461`.
- Downloaded `results.zip` SHA256: `f29851d96396114b3438d4972e3bc2986972520dfe970fc24c1f7436c48542a1`.
- ZIP integrity passed. All nine evaluated source files, after newline normalization, match the prepared candidate; both evaluated adapter weight files match the staged official sample weights.
- Mean duration is `mean(duration_seconds) / 60`. Empty means `patch_chars == 0`; timeout and context-error counts use explicit harness errors.

Full private traces, raw run files and ZIP remain local. Commit only this small summary and the corresponding experiment-log row. Preserve the evaluated variant; do not tune it against these dev failures or rerun solely to chase 7/30.

Compact, per-task evidence is in [edit-early-dev-20261125.json](edit-early-dev-20261125.json). It contains outcome metrics and provenance, without full traces, patches or weights.
