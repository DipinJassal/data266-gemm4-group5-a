# PR #18 — Saved-run metric evidence

Offline verification of `team-b/tools/analyze_multi_agent_traces.py` against **already fetched** Team B Kaggle artifacts. No new GPU / Kaggle launch. Raw traces and run folders are **not** committed.

Analyzer tip used for this write-up: commit `a554359` on `b/multi-agent-metrics`.

## Trace provenance (local worktrees)

| Label | Variant | Split | Local run directory |
|---|---|---|---|
| V1 smoke | `analyzer-plan` | smoke | `_wt-team-b-v1-kaggle-prep/team-b/kaggle/runs/team-b-variants-analyzer-plan/smoke/20261123T073029Z` |
| V2 smoke | `diff-critic` | smoke | `_wt-team-b-v2-kaggle-prep/team-b/kaggle/runs/team-b-variants-diff-critic/smoke/20261124T070909Z` |
| V2 dev | `diff-critic` | dev | `_wt-team-b-v2-kaggle-prep/team-b/kaggle/runs/team-b-variants-diff-critic/dev/20261124T102323Z` |

Nested harness path pattern (under each run dir):

`results/team-b__variants__<variant>/<split>/harness_results.jsonl`
`results/team-b__variants__<variant>/<split>/swegemma/traces/trace_<instance_id>.json`

## Aggregate metrics (CLI + harness)

Regenerated with:

```bash
python team-b/tools/analyze_multi_agent_traces.py \
  --run-dir <RUN_DIR> \
  --variant <analyzer-plan|diff-critic> \
  --output-dir team-b/analysis/<label>/   # gitignored local scratch
```

| Run | Tasks | Traces present | Resolved | Sub-agent invoked |
|---|---:|---:|---:|---|
| V1 smoke `20261123T073029Z` | 10 | 10/10 | **0/10** | analyzer **8/10** |
| V2 smoke `20261124T070909Z` | 10 | 10/10 | **1/10** | critic **1/10** (`fastapi_13537`) |
| V2 dev `20261124T102323Z` | 30 | 30/30 | **6/30** | critic **13/30** |

CLI `critic_response_class` / `structured_plan_observed` stayed `not_available` on these runs (see limitations below). Invocation and resolve counts above match direct `harness_results.jsonl` + `function_name` event extraction.

### V2 critic-invoked task ids (dev)

`fastapi_14077`, `fastapi_14258`, `fastapi_14301`, `fastapi_14303`, `fastapi_14356`, `fastapi_14492`, `requests_7315`, `requests_7433`, `rich_3052`, `rich_3278`, `rich_3675`, `rich_3718`, `rich_3905`.

## Completed critic feedback — direct trace inspection

Definition used here (stricter than the CLI field): a **completed critic return** is observed when the critic finishes with protocol text `OK` or `Problems:` **and** the parent receives that payload (system observation with `tool_name: diff_critic_agent` and `{"raw": "OK"}` / problems text).

This is **not** inferred solely from `critic_response_class=not_available`.

### V2 smoke — zero completed returns (direct)

On `trace_fastapi_13537.json`:

1. Parent (`swe_baseline_agent` / `main_lora`) calls `diff_critic_agent` after a successful repro (step 15).
2. Following steps are authored by `diff_critic_agent` (`tool_lora`) and use `run_command` / `read_file` to inspect the diff.
3. The trace **ends inside the critic** (last step still critic tool use). There is **no** critic final `OK` / `Problems:` message and **no** system observation returning critic output to the parent.

Therefore smoke “zero completed critic feedback” is an **observed absence of a completed return**, not a parser-only NA. The smoke PASS is **not** attributed to critic feedback (patch existed before the critic call; critic never finished).

### V2 dev — completed returns present on some tasks

Direct inspection of the 13 critic-invoked traces:

| Outcome | Count | Task ids |
|---|---:|---|
| Completed return `OK` (critic final message + parent `{"raw":"OK"}`) | **5** | `fastapi_14258`, `fastapi_14492`, `requests_7315`, `requests_7433`, `rich_3675` |
| Critic exit with **empty** parent raw (`{"raw":""}`) | 4 | `fastapi_14077`, `fastapi_14301`, `rich_3718`, `rich_3905` |
| No parent critic-return observation (cut off mid-critic) | 4 | `fastapi_14303`, `fastapi_14356`, `rich_3052`, `rich_3278` |
| Completed `Problems:` return | **0** | — |

Among the **6** resolved (PASS) tasks:

| Task | Critic invoked? | Completed critic return? |
|---|---|---|
| `fastapi_14077` | yes | no (empty raw) |
| `fastapi_14301` | yes | no (empty raw) |
| `fastapi_14492` | yes | **yes (`OK`)** |
| `rich_3278` | yes | no (cut off) |
| `rich_3718` | yes | no (empty raw) |
| `rich_3905` | yes | no (empty raw) |

`fastapi_14492` is the only PASS with a completed `OK` return. That return **approves** an already-written patch; there is **no** direct evidence of critic-driven edits causing the resolve. No PASS is attributed to critic feedback beyond “critic was reached / sometimes returned OK.”

## Response-extraction limitation (CLI)

`analyze_multi_agent_traces.py` classifies `critic_response_class` only from **text attached to extracted critic tool-call events**. On real Team B swegemma traces:

- The critic **invocation** step has `tool_calls[].function_name = diff_critic_agent` and usually **no** response body.
- The protocol answer (`OK` / `Problems:`) appears later as a **critic-authored** `message` and/or a **system** observation `{"raw": "..."}` with `extra.tool_name = diff_critic_agent`.

Those return shapes are therefore often reported as `critic_response_class=not_available` even when a completed return is visible under manual inspection (as in the 5 OK cases above). Invocation counts remain reliable via `function_name`. Treat CLI response-class aggregates as best-effort; use direct trace checks for “completed feedback” claims.

## Reproduce locally

Requires the three saved run directories above (or equivalent fetches). From repo root on `b/multi-agent-metrics`:

```bash
python -m unittest team-b.tools.tests.test_analyze_multi_agent_traces -v

python team-b/tools/analyze_multi_agent_traces.py \
  --run-dir ../_wt-team-b-v1-kaggle-prep/team-b/kaggle/runs/team-b-variants-analyzer-plan/smoke/20261123T073029Z \
  --variant analyzer-plan \
  --output-dir team-b/analysis/v1-smoke-evidence/

python team-b/tools/analyze_multi_agent_traces.py \
  --run-dir ../_wt-team-b-v2-kaggle-prep/team-b/kaggle/runs/team-b-variants-diff-critic/smoke/20261124T070909Z \
  --variant diff-critic \
  --output-dir team-b/analysis/v2-smoke-evidence/

python team-b/tools/analyze_multi_agent_traces.py \
  --run-dir ../_wt-team-b-v2-kaggle-prep/team-b/kaggle/runs/team-b-variants-diff-critic/dev/20261124T102323Z \
  --variant diff-critic \
  --output-dir team-b/analysis/v2-dev-evidence/
```

For completed-feedback checks, open `swegemma/traces/trace_<id>.json` and inspect steps after the `diff_critic_agent` tool call: critic `message == "OK"` / `Problems:` and the following system observation with `tool_name: diff_critic_agent`.

## Out of scope

- Committing raw traces, weights, or `team-b/kaggle/runs/**`
- New Kaggle kernels / official submissions
- Changes to V1/V2 variant code
