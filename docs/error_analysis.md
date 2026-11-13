# Baseline error analysis (Khushi, due Nov 12)

Analysis of the baseline dev run of **Nov 10, 2026**: 30 tasks, unmodified sample agent, 1 min and 10 tool calls per task.
Written Nov 12, 2026 from the run ZIP Dipin shared. **Observed** means read directly from the run files.
**Inferred** and **Hypothesis** mean our interpretation of those files.

## 1. Evaluation configuration and method

**Run (observed, `run_info.json` and `README.txt` in the ZIP)**

| Item | Value |
|---|---|
| Variant | `baseline` (unmodified Kaggle `sample_submission/`), git `b46b016`, not dirty |
| Model | `gemma-4-31b-it-qat-w4a16-ct`, adapters `main_lora` and `tool_lora` (zero-initialized dummies, so effectively the base model) |
| Hardware | Kaggle, 4× L4, vLLM start 411.5 s |
| Split | `dev`, 30 tasks; IDs match `harness/splits/dev.txt` exactly |
| Budget per task | 1.0 min, 10 tool calls, 50 turns, 60 s command timeout, 300 s verification timeout |
| Run time | 2026-11-10 18:21 to 19:02 UTC |

**Evidence used.** The ZIP is `baseline-dev-20261110.zip`, SHA-256 `72541af8…80998b9`, 99 files. It is not committed to the repo; Dipin's copy is
`harness/runs/baseline-dev-20261110.zip` (git-ignored). From it we used:

- `harness_results.jsonl`: outcome, time and tool calls per task
- `submission.csv`: the exact patch each task produced
- `traces/trace_<task>.json`: every step, thought, tool call and tool result
- `logs_plain/<task>.txt`: readable transcripts
- `kaggle_kernel.log`

To check whether the agent opened and edited the right files, we compared each trace with the reference `patch` in the competition's
`tasks.jsonl` (downloaded with the Kaggle CLI into `data/`, git-ignored).

**Method.**
1. Each task gets one **primary label** for its final patch, so the labels sum to 30.
2. Each task also gets any number of **contributing flags** for behavior seen in its trace.
3. All counts were computed by script from the files above, not by hand.
4. No V1 prompt or variant was changed based on this analysis. V1 was finalized before the ZIP was opened.

## 2. Baseline performance (verified)

The run files match the figures in CLAUDE.md exactly.

| Metric | CLAUDE.md | Run files |
|---|---|---|
| Resolved | 2/30 = 6.7% | 2/30 (`fastapi_14492`, `rich_3905`) |
| Empty patch | 20 | 20 |
| Non-empty patch that failed hidden tests | 8 | 8 |
| Per repo | fastapi 1/15, rich 1/11, requests 0/3, httpx 0/1 | same |
| Average time per task | 1.1 min | 65.3 s = 1.09 min (min 41.5 s, max 135.7 s) |
| Tool calls per task | not stated | mean 6.6; 14 tasks reached 10 |
| Ended by "Agent exceeded session timeout (1.0 min)" | not stated | 28/30 (every task except the 2 passes) |

## 3. Failure categories

### 3.1 Primary label per task (sums to 30)

This is the table from the original template, filled in. Rules are below it.

| Failure type | Count | Task IDs |
|---|---|---|
| Wrong file found | 0 as primary | No final patch changed only non-reference source files. **This does not mean localization was fine:** 5 tasks never opened any reference-patch file (flag L), 2 edited only part of a multi-file fix (flag P), and "opened a reference file" is file-level only. The 5 flag-L tasks ended with no source change, so their primary label is empty/invalid diff |
| Right file, wrong fix | 5, shared with the row below | `fastapi_14077`, `fastapi_14303`, `requests_7315`, `requests_7433`, `rich_4070` |
| Broke other tests | included above | This run did not save Phase 2 test output, so a wrong fix and a regression can't be told apart |
| Timeout or looping | 0 as primary | Not a mutually exclusive outcome. The timeout ended 28/30 sessions (including all 28 failures), so it is recorded as contributing flag T alongside the patch outcome. Exact repetition (looping) was rare: flag D, 4 tasks |
| Empty/invalid diff | 23 | the 20 EMPTY tasks, plus 3 FAIL tasks whose patch contains **only a scratch script**: `fastapi_12942`, `fastapi_14258`, `fastapi_14356` |
| *(Resolved)* | 2 | `fastapi_14492`, `rich_3905` |

**Rules:**
- *Empty/invalid diff:* the final patch changes no source file (`submission.csv`). Scratch scripts such as `repro.py` don't count as source.
- *Right file, wrong fix / broke other tests:* the patch changes at least one source file that is also in the reference patch, and the hidden tests failed.
- *Wrong file found* would apply if the patch changed only non-reference source files. No task did that.

### 3.2 Contributing flags (multi-label, from traces)

| Flag | Meaning | Tasks |
|---|---|---|
| **T** | Session ended by the 1-minute timeout | 28 |
| **C** | Reached the 10-tool-call cap. In 7 tasks a later call returned `BudgetExceeded` | 14 |
| **G** | Cut off while generating: 15 s or more passed after the last tool result with no further call | 12 |
| **R** | Read the same file more than once (any line range) | 23 |
| **D** | Exact duplicate read (same file and same range) | 4 tasks (5 repeats) |
| **M** | Malformed tool-call arguments | 8 |
| **S** | Scratch script left in the final patch | 6 |
| **L** | Never opened any file from the reference patch | 5 |
| **P** | Edited some but not all reference source files (multi-file fixes) | 2 |
| **X** | The agent's own reproduction script crashed | 3 |

## 4. Per-task analysis

How to read the columns:
- *Opened a ref. file* means the trace shows `read_file` on a source file from the reference patch.
- *First source edit* is the first **successful** `edit_file`/`write_file` on a non-scratch file, given as the 1-based tool-call number and the seconds from the start of the task.
- *Ran a check* means a `run_command` that ran a Python script.

Evidence for each row is in `traces/trace_<task>.json` and `logs_plain/<task>.txt` in the ZIP.

| Task | Outcome | Time (s) | Tool calls | Opened a ref. file | First source edit (call #, s) | Ran a check | Primary label | Flags |
|---|---|---:|---:|---|---|---|---|---|
| `fastapi_12942` | FAIL | 66.9 | 2 | no | none | yes, before edit only | Empty/invalid diff | T S L X |
| `fastapi_13207` | EMPTY | 63.8 | 10 | no | none | no | Empty/invalid diff | T C R M L |
| `fastapi_13713` | EMPTY | 63.5 | 10 | yes | none | no | Empty/invalid diff | T C R |
| `fastapi_14077` | FAIL | 66.8 | 10 | yes | #7, 40.7 | no | Wrong fix or broke tests (not separable) | T C P |
| `fastapi_14186` | EMPTY | 63.5 | 1 | yes | none | no | Empty/invalid diff | T G |
| `fastapi_14246` | EMPTY | 63.6 | 10 | no | none | no | Empty/invalid diff | T C R L |
| `fastapi_14258` | FAIL | 67.4 | 10 | yes | none | yes, before edit only | Empty/invalid diff | T C R M S X |
| `fastapi_14262` | EMPTY | 63.5 | 10 | yes | none | no | Empty/invalid diff | T C R |
| `fastapi_14301` | EMPTY | 63.6 | 7 | yes | none | no | Empty/invalid diff | T G R |
| `fastapi_14303` | FAIL | 66.3 | 6 | yes | #5, 57.7 | yes, after edit | Wrong fix or broke tests (not separable) | T R S |
| `fastapi_14306` | EMPTY | 63.9 | 10 | yes | none | no | Empty/invalid diff | T C G R |
| `fastapi_14356` | FAIL | 66.9 | 10 | yes | none | yes, before edit only | Empty/invalid diff | T C R S |
| `fastapi_14492` | PASS | 41.5 | 6 | yes | #3, 17.0 | no | Resolved | - |
| `fastapi_14616` | EMPTY | 64.0 | 10 | yes | none | no | Empty/invalid diff | T C G R |
| `fastapi_15588` | EMPTY | 64.7 | 1 | yes | none | no | Empty/invalid diff | T G |
| `httpx_3672` | EMPTY | 60.6 | 5 | yes | none | no | Empty/invalid diff | T R |
| `requests_7315` | FAIL | 63.1 | 10 | yes | #8, 46.3 | yes, after edit | Wrong fix or broke tests (not separable) | T C R M S |
| `requests_7427` | EMPTY | 61.6 | 5 | yes | none | no | Empty/invalid diff | T G R D M |
| `requests_7433` | FAIL | 135.7 | 10 | yes | #5, 24.8 | yes, after edit | Wrong fix or broke tests (not separable) | T C R S X |
| `rich_3052` | EMPTY | 61.9 | 3 | yes | none | no | Empty/invalid diff | T G R |
| `rich_3063` | EMPTY | 61.9 | 1 | yes | none | no | Empty/invalid diff | T G |
| `rich_3278` | EMPTY | 61.7 | 2 | yes | none | no | Empty/invalid diff | T R |
| `rich_3521` | EMPTY | 61.9 | 6 | yes | none | no | Empty/invalid diff | T G R D M |
| `rich_3675` | EMPTY | 62.0 | 10 | yes | none | no | Empty/invalid diff | T C R M |
| `rich_3718` | EMPTY | 62.1 | 2 | yes | none | no | Empty/invalid diff | T G R |
| `rich_3905` | PASS | 64.7 | 10 | yes | #6, 43.1 | yes, after edit | Resolved | C R |
| `rich_3930` | EMPTY | 62.0 | 6 | yes | none | no | Empty/invalid diff | T R D M |
| `rich_3935` | EMPTY | 61.9 | 2 | no | none | no | Empty/invalid diff | T G L |
| `rich_4070` | FAIL | 66.6 | 3 | yes | #3, 58.7 | no | Wrong fix or broke tests (not separable) | T R P |
| `rich_4076` | EMPTY | 61.9 | 10 | no | none | no | Empty/invalid diff | T C G R D M L |

**Notes on individual tasks (observed):**
- `fastapi_14258`: found `fastapi/routing.py`, the file in the reference patch, then made 3 `edit_file` calls on it. All 3 failed with
  "mandatory input parameters are not present: old_string", because the argument name was garbled (call #11–13).
  The final patch contains only `reproduce_issue.py`.
- `fastapi_12942`: spent 51 s generating a scratch script before its first tool call. The script then crashed (pydantic traceback).
  The task never opened `fastapi/_compat.py`.
- `fastapi_14356`: wrote and edited `reproduce_bug.py`, read the reference file `fastapi/dependencies/utils.py`, but never edited it.
- `fastapi_14303`: the agent's own check printed "Test passed!" after its edit to the reference file, yet the hidden tests failed.
  The patch also contains `reproduce_issue.py`.
- `requests_7433`: the reproduction script crashed with `AttributeError: 'Request' object has no attribute ...` because it misused the API,
  so its check verified nothing. The agent called `submit_patch` at 55.1 s after a `BudgetExceeded` reply.
- `fastapi_14077`: edited 2 of the 3 reference source files. `docs_src/handling_errors/tutorial005.py` was not edited.
  A successful edit to `pyproject.toml` is **not** in the final patch, and the reason is unknown (see §6).
- `rich_4070`: made its only edit at 58.7 s, to 1 of the 9 reference source files.
- `rich_3905` (pass): deleted its scratch files with `rm repro.py test_enabled.py` before its second `submit_patch`.
- `rich_4076`: four `grep -rn ... /workspace/rich...` searches matched nothing. It then requested the malformed path
  ``rich/markdown.py`,start_line:151`` three times in a row, and each request failed with "not found in sandbox".

## 5. Behavioral patterns

### Confirmed observations

1. **Most failures produced no source change before the time ran out.**
   - 23/30 final patches change no source file.
   - In 18 of those 23, the agent had already opened a file from the reference patch (25/30 overall), but only 7/30 tasks ever made a successful source edit.
   - Earliest successful source edits ranged from call #3 to call #8 (17.0–58.7 s). In 5 of the 7 they came after 40 s.
2. **Time went to waiting for the model, not to tools.** The 30 tasks used 1,960 s of wall-clock time in total (`harness_results.jsonl`). From trace timestamps:

   | Part of the session | Time | Share of wall-clock |
   |---|---:|---:|
   | Waiting for the model between a tool result and the next tool call | 1,231 s | 63% |
   | After the last tool result until the session ended (no further call) | 651 s | 33% |
   | Tool execution | 9 s | 0.4% |
   | Setup before the task prompt | 68 s | 3.5% |

   - "Waiting for the model" is measured from timestamps. It includes generation and any serving latency; these files can't separate the two.
   - Most of the post-last-result time is in the 12 flag-G tasks, where the agent was still generating when cut off. It also includes the unexplained extra time in `requests_7433` (see §6).
   - Effective throughput (completion tokens divided by the gap before each call, for steps over 100 tokens) had a median of 29.3 tokens/s (IQR 26.7–30.8).
   - Median time to the first tool call was 9.2 s (range 4.7–51.1).
   - 12 tasks (flag G) were cut off 15–56 s after their last tool result. Five of them made only 1–2 calls.
3. **The 10-call cap was reached in 14 tasks,** but the session was still ended by the 1-minute timeout in all of them except the pass `rich_3905`.
   In those 7 tasks, calls made after the cap returned `BudgetExceeded`, and the agents kept trying until the timeout.
   `submit_patch` still succeeded after a `BudgetExceeded` reply in `requests_7433`. The harness's call counting
   is not fully clear: `rich_3905` reports 10 calls, but its trace shows 12 with no `BudgetExceeded`.
4. **Malformed tool calls happened in 8/30 tasks.** Examples:
   - argument names like `start_line"` and `"end_line"`
   - a garbled `edit_file` key
   - `write_file` with no `filepath`
   - a file path containing `` `,start_line:151 ``

   Most `read_file` calls with a garbled key still returned `ok`. In `fastapi_14258` the malformed edits stopped the only fix attempt.
5. **Verification was rare and weak.**
   - No task ran the repository's own tests (no `pytest` or `unittest` command anywhere).
   - The 12 check runs were all ad-hoc scripts the agent wrote. 7 tasks ran one, and only 4 ran it after a source edit.
   - 3 of these scripts crashed for reasons unrelated to the fix (flag X).
   - `submit_patch` was called in 3 tasks: the 2 passes and `requests_7433`.
6. **Scratch files pollute patches.**
   - 6 of the 8 non-empty failing patches contain a scratch script (`repro.py`, `reproduce_issue.py`, `reproduce_bug.py`).
   - 3 contain nothing else.
7. **Re-reading is common but mostly not exact repetition.**
   - 23 tasks read some file more than once (63 re-reads in total).
   - Only 5 repeats were exact duplicates (same file and range), in 4 tasks.
   - Different ranges are expected, because `read_file` returns at most 150 lines.
8. **The search tools were almost unused.**
   - `search_similar_code` was never called, `get_code_neighbors` was called twice (one task), and `get_code_subgraph` was never called.
   - 17 tasks used shell search (`grep`/`find`/`ls`/`cat`).
   - The `code_analyzer` sub-agent was never called.

### Hypotheses (not tested)

- **H1:** at this budget, the main cause of failure is generation latency relative to the 1-minute limit. If thinking tokens are generated at the
  measured rate (unverified), the 4,096-token thinking budget alone would take about 140 s, which exceeds the whole per-task budget.
- **H2:** some "wrong patch" failures come from incomplete multi-file fixes (`fastapi_14077`, `rich_4070`), not from wrong logic.
- **H3:** scratch files in patches may hurt scoring. We can't tell from this run, because Phase 2 output was not saved.
- **H4:** malformed tool arguments may be a property of the quantized model's tool-call formatting, not of the prompt.

## 6. Limitations and missing evidence

- **No Phase 2 output.** This run did not save the pytest log from scoring, so "wrong fix" and "broke other tests" can't be told apart.
  `harness_results.jsonl` has `test_exit_code` (1 or 2 for failed patches), which we report but do not interpret.
  Later runs save `task_details/` (CLAUDE.md, Nov 12).
- **The reference patch is one valid fix, not the only one.** "Opened a reference file" means file-level localization only, not the right function.
- **One run, temperature 0.2, 30 tasks.** One task is 3.3 points, and no run-to-run variance is measured.
- **Unfinished generations aren't logged.** For flag-G tasks we can't see what the agent was generating when it was cut off.
- **Unexplained run details:**
  - `requests_7433` reports 135.7 s of wall time, but the kernel log shows the agent timed out at 1m 00s.
  - 11 traces contain more tool calls than `tool_calls` reports, because rejected calls and `submit_patch` count differently.
  - The successful `pyproject.toml` edit in `fastapi_14077` is missing from its final patch.
- **Token data.** `total_tokens` in `harness_results.jsonl` is 0 for every task. Token figures here come from the traces' `final_metrics` and step `metrics`.
- **Analysis scripts are not in the repo.** We used three read-only Python scripts. They can be added if the team wants this analysis rerunnable.
- **Budget dependence.** All findings are for the 1-minute / 10-call budget. Behavior at 4.5 min / 50 calls (V2) may differ and must be measured separately.

## 7. Implications for future work

These are research questions, not claims of improvement. None of this has been tested.

- **Budget first.** 28/30 tasks timed out, and about 96% of wall-clock time was spent waiting for the model against 0.4% on tools.
  So prompt or sampling effects measured at the 1-minute budget would mostly measure the timeout. This supports using the V2 budget (`dipin-step-budget-v1`) as the control for prompt variants, which is still pending
  team confirmation (CLAUDE.md, "Everyone (proposal …)").
- **Thinking budget versus time budget.** Effective throughput (about 29 tokens/s) is a measurable constraint. This belongs to Sarvesh's sampling area
  (thinking on/off), not to the prompt variants.
- **Edit before cut-off.** 18 tasks opened a reference file but produced no source change. V1's "first edit within about 10 tool calls" was designed
  *before* this analysis. Whether it helps must be measured on V1 against V2 traces, not assumed.
- **Patch hygiene.** Scratch files appear in 6 of 8 failing patches. This affects the combined agent's patch-hygiene check (Dipin) and the V1 checklist.
- **Tool-call reliability.** Malformed arguments in 8/30 tasks are worth tracking in every later run.
- **Evidence for V2 (anti-looping).** At this budget, exact repetition is rare (5 repeats). Looping should be judged on V2-budget traces.
- **Dev-set hygiene (rule 3).** These patterns come from dev tasks. Before designing V2 or V3 around them, confirm the same patterns on smoke or train
  runs, so variants aren't tuned to the dev set.
