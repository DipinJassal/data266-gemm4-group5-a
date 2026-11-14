# Baseline profile (Sarvesh)

Time / turns profile of the **unmodified sample agent** on the team `dev` split.
Numbers below are from the Nov 10, 2026 harness run (`baseline-dev-20261110.zip`), verified by Khushi
against the raw run files (see `docs/error_analysis.md`). This doc is the short ops profile; failure
labels live in the error analysis.

## Budget (important)

From `baseline/eval_config.yaml` (unchanged sample):

| Setting | Value |
|---|---|
| `max_time_minutes` | **1** |
| `max_tool_calls` | **10** |
| `max_turns` | 50 |
| Command timeout | 60 s |
| Model | `gemma-4-31b-it-qat-w4a16-ct` |
| Sampling | temp 0.2, top_p 0.95, thinking_budget 4096 (`configs/sampling.yaml`) |

**Implication:** the 1-minute / 10-call cap cuts most tasks off before a source edit. Low baseline score
is expected; do not treat a prompt/sampling change on this budget as a fair A/B without also comparing
at the V2 budget (4.5 min / 50 calls).

## Run summary

| Item | Value |
|---|---|
| Split | `dev` (30 tasks) |
| Hardware | Kaggle 4× L4; vLLM start ~411.5 s |
| Wall window | 2026-11-10 18:21–19:02 UTC |
| Resolved | **2/30 = 6.7%** (`fastapi_14492`, `rich_3905`) |
| Empty patches | 20 |
| Non-empty patches that failed | 8 |
| Per repo | fastapi 1/15, rich 1/11, requests 0/3, httpx 0/1 |

## Average time and turns (tool calls)

| Metric | Value |
|---|---|
| Mean wall time / task | **65.3 s ≈ 1.09 min** (min 41.5 s, max 135.7 s) |
| Mean tool calls / task | **6.6** |
| Tasks that hit 10-call cap | **14 / 30** |
| Tasks ended by "session timeout (1.0 min)" | **28 / 30** (all failures; both passes finished in budget) |
| Median time to first tool call | 9.2 s (range 4.7–51.1) |
| Effective generation throughput | ~29.3 tokens/s median (from trace step metrics) |

"Turns" in practice ≈ tool-call steps in the trace (plus generation gaps). Token counters in
`harness_results.jsonl` were 0 for this run; token rates come from trace `final_metrics` / step metrics.

### Where the minute went (all 30 tasks, 1,960 s total)

| Part of the session | Time | Share |
|---|---:|---:|
| Waiting for the model (between tool result → next call) | 1,231 s | 63% |
| After last tool result until cut-off (no further call) | 651 s | 33% |
| Tool execution | 9 s | **0.4%** |
| Setup before task prompt | 68 s | 3.5% |

Almost all wall time is model wait / generation against the 1-minute cap, not tool I/O.

## Slowest tasks

Wall seconds from `harness_results.jsonl` (dev run). Top of the list:

| Task | Outcome | Time (s) | Tool calls | Notes |
|---|---|---:|---:|---|
| `requests_7433` | FAIL | **135.7** | 10 | Kernel log shows agent timeout at 1m; wall &gt; budget is unexplained in this run |
| `fastapi_14258` | FAIL | 67.4 | 10 | Scratch-only patch; malformed edit args |
| `fastapi_12942` | FAIL | 66.9 | 2 | ~51 s before first tool call |
| `fastapi_14356` | FAIL | 66.9 | 10 | Scratch script; never edited reference file |
| `fastapi_14077` | FAIL | 66.8 | 10 | Partial multi-file edit |
| `rich_4070` | FAIL | 66.6 | 3 | Late first edit (~58.7 s) |
| `fastapi_14303` | FAIL | 66.3 | 6 | Agent's own check passed; hidden tests failed |

Fastest resolved: `fastapi_14492` at **41.5 s** (6 calls). Other pass: `rich_3905` at 64.7 s (10 calls).

Most EMPTY tasks cluster at **~61–64 s** (timeout shortly after the 1-minute mark).

## Longest tool outputs

Harness hard caps (not tunable in the agent):

- `run_command` output: **5,000 characters**
- `read_file`: **150 lines** per call

In this baseline run:

- Total tool-execution time across 30 tasks was only **~9 s**, so raw tool payloads were not the bottleneck.
- Agents relied on `read_file` / ad-hoc `run_command` scripts; **no task ran repo `pytest`/`unittest`**.
- Search tools were almost unused (`search_similar_code` never; `get_code_subgraph` never;
  `get_code_neighbors` twice in one task).
- Exact per-call output byte lengths were not exported into a committed summary; recompute from
  `traces/trace_<task>.json` in the run ZIP if needed. Practical takeaway for the profile: **outputs are
  truncated by the harness long before they dominate the 1-minute budget** — generation latency does.

## What to hand to the team

- Profile (this file) + run guide (`docs/run_guide.md`).
- Full failure labels: Khushi's `docs/error_analysis.md`.
- Raw evidence: `harness/runs/baseline-dev-20261110.zip` (git-ignored; ask Dipin if you need a copy).
- Experiment log row: baseline, owner Sarvesh/Dipin harness, change "none", dev **2/30**, status logged.
