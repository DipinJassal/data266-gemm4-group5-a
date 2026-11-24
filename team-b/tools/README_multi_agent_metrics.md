# Multi-agent trace metrics (Parth)

Offline analysis for Parth’s Team B multi-agent variants:

| Variant | PR | Experiment |
|---|---|---|
| `analyzer-plan` | #13 | V1 analyzer-first plan handoff |
| `diff-critic` | #14 | V2 single-round critic |

This tool **does not** launch Kaggle jobs, run models, or edit `team-b/docs/experiment_log.csv`.
It only reads a **saved** run directory (from `team-b/kaggle/run_kaggle.py` / shared harness) and writes metrics under a separate output folder.

## Expected inputs

A run directory that contains (possibly nested) artifacts written by `team-b/kaggle/kaggle_runner.py`:

| Path | Role | Required? |
|---|---|---|
| `**/harness_results.jsonl` | Per-task summary (`instance_id`, `resolved`, `wall_seconds`, `tool_calls`, `patch_chars`, `error`, …) | Strongly recommended |
| `**/run_info.json` | Budgets, model, split, git rev | Optional |
| `**/task_details/<instance_id>.json` | Field-by-field swegemma result (traces often **skipped** here) | Optional |
| `**/swegemma/traces/**` | Detailed tool / agent events when swegemma emits them | Required for ordering metrics |

### Schema findings (from this repo)

Observed `harness_results.jsonl` fields (Team A sample under `docs/runs/...` on `main`):

`instance_id`, `repo`, `resolved`, `duration_seconds`, `wall_seconds`, `tool_calls`, `test_exit_code`, `patch_chars`, `error`, `total_tokens`

Team B’s runner documents that `SessionTrace` is **not** embedded into `task_details/` (field skipped; see `save_full_result`). Trace order for analyzer/critic therefore depends on `swegemma/traces/` (or equivalent JSON that still contains tool/function-call nodes).

**No frozen official swegemma trace schema is checked into this repository.** Event extraction is best-effort over several JSON shapes:

- Real Team B Kaggle downloads (Nov 2026): `swegemma/traces/trace_<instance_id>.json` with `steps[].tool_calls[].function_name`
- Older / synthetic fixtures: `name`, `tool`, `function_call.name`, nested `events` lists

Unrecognized files yield `not_available`, not zeros.

## CLI

```bash
# From repo root, after a Team B Kaggle/local harness run has finished and been fetched:
python team-b/tools/analyze_multi_agent_traces.py \
  --run-dir team-b/kaggle/runs/analyzer-plan/smoke/<UTC>/ \
  --variant analyzer-plan \
  --output-dir team-b/analysis/analyzer-plan-smoke-<UTC>/

python team-b/tools/analyze_multi_agent_traces.py \
  --run-dir team-b/kaggle/runs/diff-critic/smoke/<UTC>/ \
  --variant diff-critic \
  --output-dir team-b/analysis/diff-critic-smoke-<UTC>/
```

`team-b/analysis/` is git-ignored (local scratch). Do not commit raw analysis dumps unless the team explicitly wants a small summary in `team-b/results/`.

## Outputs

| File | Contents |
|---|---|
| `per_task.csv` | One row per task: harness fields + derived metrics + `trace_status` + notes |
| `summary.json` | Aggregates, rates, availability reasons, schema notes |
| `report.md` | Human-readable summary for PR / lab notes |

### Metric classes

1. **Observed** — copied from `harness_results.jsonl` / `run_info.json` when present.
2. **Derived** — analyzer/critic ordering and response-class heuristics from extracted events.
3. **Unavailable** — `not_available` when traces/fields are missing (never silently coerced to `0`).

## How metrics are computed

### V1 `analyzer-plan`

| Metric | Needs |
|---|---|
| Task count / resolution / patch empty / runtime / tool_calls | `harness_results.jsonl` |
| Analyzer invoked / call count / retries | Trace events naming `code_analyzer_agent` (or `code_analyzer`) |
| Analyzer-before-first-edit | Ordered events: first analyzer index &lt; first `edit_file`/`write_file`; `not_available` if analyzer ran but no edit event exists |
| Structured plan observed | Analyzer event **text** matching plan/root-cause/file-list cues; else `not_available` |

### V2 `diff-critic`

| Metric | Needs |
|---|---|
| Critic invoked / count / &gt;1 call | Trace events naming `diff_critic_agent` (or `diff_critic`) |
| Critic-before-submit | First critic index &lt; first `submit_patch`; `not_available` if critic ran but no submit event exists |
| OK vs problems / issue count | Critic response text (`OK` vs `Problems:` numbered lines) |
| Edits after critic | Any `edit_file`/`write_file` **after** first critic call |

**Important:** `edits_after_critic` only means a source edit happened after the critic ran. It does **not** prove the feedback was correct or that the agent followed it.

Trace files are matched by **exact** task id. Accepted filenames include `trace_<id>.json` and `<id>.json`, plus `traces/<id>/trace.json`. Substring globs are not used. If `harness_results.jsonl` is missing, the CLI still builds a report from `task_details/` / `traces/` stubs; resolution fields stay `not_available`.

## Smoke vs dev vs official Kaggle score

| Split / score | Use |
|---|---|
| Smoke (10 or `--max-tasks`) | Debugging / metric plumbing; iterate freely |
| Dev (30, once final) | Validation used for selection; label as such in the experiment log |
| Official Kaggle submission | Held-out team score — **never** claimed from this tool’s local/smoke output |

Copy rates you trust into Parth’s multi-agent report section manually. Do not overwrite Ashmitha’s score charts or Naveen’s error-analysis labels.

## Tests

Synthetic-only unit tests (no GPU):

```bash
python -m unittest team-b.tools.tests.test_analyze_multi_agent_traces -v
# or:
python team-b/tools/tests/test_analyze_multi_agent_traces.py -v
```

## After Parth’s first Kaggle diagnostic

1. Fetch the run with `python team-b/kaggle/run_kaggle.py --fetch team-b/variants/analyzer-plan smoke`.
2. Point `--run-dir` at the downloaded folder under `team-b/kaggle/runs/`.
3. Confirm `swegemma/traces/` (or rich `task_details/`) exist; if missing, summary rates for analyzer/critic order will stay `not_available`.
4. Attach `report.md` / key `summary.json` rates when updating the multi-agent report draft (PR #16).
