# Combined agent v1: dev result (negative)

**Run:** Kaggle kernel `g5a-eval-combined-dev`, Nov 22, 4× L4, one full dev run (30 tasks), git `f88acc5`.
**Agent:** `combined/` at commit `f88acc5` (branch `dipin/combined-v1`). Team A work only.

| Part | Owner |
|---|---|
| Structured loop prompt (base) | Khushi |
| Keep-tool-output-small rules | Dipin |
| At most one retry when the targeted check fails | Sarvesh |
| New: import check of changed modules, fix imports on rename, delete scratch files, exact new-parameter names, "edit by ~30 calls" | Dipin |
| Budget 4.0 min / 50 calls (cut from 4.5 for the 12-hour limit) | Dipin |

## Result

**4/30 = 13.3%** (fastapi 3/15, rich 1/11, requests 0/3, httpx 0/1). Below the three 5/30 variants. **Not submitted.**

| | Output trimming (5/30) | Combined v1 (4/30) |
|---|---|---|
| PASS / FAIL / EMPTY | 5 / 20 / 5 | 4 / 13 / **13** |
| Tasks with at least one successful source edit | 25/30 | **17/30** |
| Median tool calls before first edit | 5 | 8 |
| Median seconds before first edit (tasks that edited) | 76 | 101 |
| Context-window crashes | 1 | 1 |
| Avg time per task | 3.9 min | 3.8 min |

Solved: `fastapi_14077`, `fastapi_14301`, `fastapi_14492`, `rich_3905`. Lost vs the 5/30 variants: `rich_3718` (context-window crash after 8 calls).

## Why it got worse

1. **More rules, later edits.** Eight tasks that output trimming edited within 20–220 s never reached an edit
   (`fastapi_13713`, `14186`, `14262`, `14356`, `rich_3063`, `3675`, `3718`, `3935`). The traces show the agent
   reading more before editing: pre-edit `run_command` calls rose from 122 to 195. In `rich_3675` it re-read
   five overlapping windows of `rich/console.py` and never edited. Planning, exact-name and rename rules seem to make the model
   investigate longer instead of committing to a fix.
2. **The 4.0 min cut costs at most 1–2 tasks.** Only `fastapi_14246` (first edit at 263 s) and possibly
   `fastapi_14186` (219 s) edited too late in the trimming run to fit under 4.0 min. Model pacing was the same in both runs
   (median 3.3 vs 3.6 s between calls).

## Config bug found (affects every variant)

Both context-window crashes in this and the trimming run fail with:

> maximum context length is 32768 tokens. However, you requested 16384 output tokens and your prompt contains at least 16385 input tokens

`configs/sampling.yaml` has `max_output_tokens: 16384`, so vLLM rejects any request once the input passes 16,384 tokens.
Every variant so far has had only **half** of the 32K window, and this is the cause of all context crashes logged so far.

## Takeaways for the report

- Stacking prompt rules from several variants did not add up: each one tied at 5/30, and together they scored 4/30.
- The next combined version (v2) starts from the shortest prompt that reached an edit most often (output trimming),
  fixes `max_output_tokens`, and adds one short pre-submit line only.
- n = 30, one run. 4 vs 5 is within noise; 13 vs 5 empty patches and 17 vs 25 tasks with an edit are the clear signal.
