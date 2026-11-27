# lean-agent (experimental → submission candidate)

Isolated Team B variant derived from `team-b/variants/budget-fit-2`. Built as an alternative to the unmodified baseline; Ashmitha has approved it as Team B’s **next official submission candidate**. It has **not** been officially submitted to Kaggle yet.

Parth’s previously assigned official upload was the unmodified Team B baseline (`team-b/variants/base`). Lean Agent is a separate candidate with measured validation results below.

## Architecture

| Piece | Setting |
|---|---|
| Root agent | `swe_baseline_agent` |
| Model | `gemma-4-31b-it-qat-w4a16-ct` (no LoRA) |
| Tools | `run_command`, `read_file`, `edit_file`, `write_file`, `get_status`, `submit_patch` |
| Instruction | `prompts/system.md` (budget-fit-2 prompt + one appended pre-submit line) |
| Sampling | temp 0.2, top_p 0.95, `max_output_tokens` 8192, thinking_budget 4096 |
| Eval budget | **8 min** / **40** tool calls / **80** turns / **240 s** command timeout |

No `adapters/`, no `sub_agents/`, no graph retrieval tools.

## Source provenance

| Field | Value |
|---|---|
| Parent variant | `team-b/variants/budget-fit-2` |
| Source commit | `5d2c60e3d310909f9ae39bfb41bed29c8f854206` (`origin/b/budget-fit` tip; variant introduced in `0001b82`, PR #32) |
| Branch | `b/lean-agent` |

`budget-fit-2` itself is left unchanged on `origin/b/budget-fit` / PR #32.

## Three intentional changes (only)

1. **No LoRA adapter** — removed `adapter: main_lora` from `agent.yaml` so the root agent runs on the base model alone. Live Kaggle runs confirmed `adapters: []` with successful vLLM start.
2. **Fewer tools** — removed `agent_tool` (code analyzer sub-agent), `search_similar_code`, `get_code_neighbors`, and `get_code_subgraph`. Kept the six core harness tools above. Unreachable `adapters/` / `sub_agents/` / `prompts/analyzer.md` packaging was not carried forward.
3. **Pre-submit check line** — appended to the existing `prompts/system.md` (no other prompt rewrite):
   `Before submit_patch, re-read the issue and confirm your change does what it asks.`

Budget-fit-2 time and tool-call settings are preserved unchanged (8 / 40 / 80 / 240).

## Hypothesis

Removing adapter load, graph/retrieval tools, and the analyzer sub-agent may cut overhead and leave more of the budget for locating, editing, and verifying a patch.

## Inspiration

Approach inspired by the publicly discussed **public-022** competition notebook / write-up (leaner single-agent setup). This is **not** an exact reproduction of public-022.

## Results

| Split | Score | Avg min/task | Empty | Notes |
|---|---|---|---|---|
| Smoke (2-task) | **2/2** | 4.4 | 0 | Adapter-free live Kaggle; run under `team-b/kaggle/runs/team-b-variants-lean-agent/smoke/` |
| Dev (30) | **8/30** | **4.9** | 2 | PASS 8 / FAIL 20 / EMPTY 2; run `20261127T032310Z` |

Dev pass ids: `fastapi_14077`, `fastapi_14301`, `fastapi_14492`, `fastapi_14616`, `rich_3063`, `rich_3278`, `rich_3718`, `rich_3905`.

Compared with Team B base dev **7/30** (avg 3.7 min): lean-agent is **above** the prior ≥6/30 / ≤5.5 min candidate gate and above base resolve count on this one validation run. Dev was used for selection, so the score may be optimistic relative to a held-out Kaggle public score.

Runtime evidence (`run_info.json` on the dev run): Python 3.12.13, 4× NVIDIA L4, budgets 8 min / 40 tools / 80 turns, `adapters: []`.

## Limitations

- One smoke diagnostic and one full-dev run only; no official Kaggle submission / public score yet (`kaggle_score` left empty in the experiment log).
- `run_info` recorded `dirty: true` because the variant lived as an uncommitted worktree during evaluation; behavioral files match the evaluated agent and must not be retuned for this PR.
- Dev selection scores can overstate held-out performance (same caveat as other Team B rows).
- Not an exact public-022 clone; only the three listed changes vs budget-fit-2 are claimed.
- `harness/validate.py` warns that 8 min > the 6 min envelope for 120 hidden tasks; mean 4.9 min/task on this dev run stayed under the 5.5 min candidate threshold.
