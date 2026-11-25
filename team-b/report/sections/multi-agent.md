# Report section — Multi-agent (Parth Patel)

Team B · Group 5 · DATA 266 · Gemma 4 Developer Agent
Status: **final multi-agent selection note (Nov 24, 2026)** — diagnostic, smoke, and **dev** logged; neither variant selected for the combined agent; **official Kaggle** submission for these variants not confirmed.

## 1. Role in Team B

I own the multi-agent architecture track. Every variant starts from `team-b/variants/base` (Team A’s budget-fixed agent: 4.5 min / 50 tool calls) and changes **one** thing. My two Phase-1 variants are independent copies of that base—not stacked on each other.

## 2. V1 — `analyzer-plan` (analyzer-first structured plan)

### Architecture
The sample agent already registers `code_analyzer_agent` via `agent_tool`. V1 does **not** add a new sub-agent. It changes:

1. Root `prompts/system.md`: call the existing analyzer once before the first `edit_file` / `write_file`; treat its plan as primary localization; at most one retry if empty/unusable; no analyzer calls after editing begins; fall back to independent search if the plan is wrong.
2. `prompts/analyzer.md`: return a ≤15-line plan — Files / Root cause / Change / Uncertainty.

Held constant: model, adapters, sampling, budgets, tool list, analyzer YAML registration.

### Hypothesis
Prompt-directed analyzer-first planning reduces wrong-file edits and undirected exploration versus the base, where the analyzer is available but not required.

### Relevance
Structured localization / planner–executor style handoffs in agentic issue resolution ([3] SWE-Protégé; [11] survey). Category-aware specialist routing ([6]) motivates keeping analysis as a separate sub-agent rather than stuffing more rules into the root prompt alone.

## 3. V2 — `diff-critic` (single-round post-edit critic)

### Architecture
New read-oriented sub-agent `diff_critic_agent` registered as a second `agent_tool`:

- Tools: `run_command`, `read_file` (prompt: git status/diff only; no edit/submit).
- Output: `OK` or ≤3 concrete problems.
- Root: after targeted tests, call critic **once**; on problems, ≤1 focused revision then `submit_patch`; never a second critic loop.
- Existing analyzer left as in base; **V1 analyzer-first policy is not imported**.

### Hypothesis
One post-edit review of the **actual** workspace diff against the issue reduces right-file/wrong-fix failures before submission ([3]).

## 4. How each differs from the fixed base

| Aspect | Base | V1 | V2 |
|---|---|---|---|
| Analyzer registered | yes | yes (unchanged YAML) | yes (unchanged YAML) |
| Analyzer-first policy | no | **yes** | no |
| Critic sub-agent | no | no | **yes** |
| Budget / model / sampling | 4.5 / 50 / shared | same | same |

## 5. Evaluation methodology

Follow Team B split roles (`TEAM_B_GUIDE.md`). Scores from different splits are **not interchangeable**:

| Split / score | Role | How to cite |
|---|---|---|
| 2-task diagnostic (`smoke` + `--max-tasks 2`) | Launcher / adapter / crash check | Label **diagnostic**, not smoke |
| Full smoke (10) | Debug time, tool use, mechanism | Label **smoke** |
| Dev (30, once per finished candidate) | Selection / validation | Label **dev** |
| Official Kaggle submission | Held-out team score | Label **official Kaggle** only |

Compare each variant to Team B base when that base run exists. Trace metrics of interest: analyzer/critic call rates, order relative to edits, completed sub-agent feedback, empty patches, wall time, tool calls, resolved tasks.

Launcher: Team B independent workflow (`team-b/kaggle/`, dataset `g5b-agents`, kernels `g5b-eval-*`). Offline metrics: `team-b/tools/analyze_multi_agent_traces.py` (PR #18).

**Runtime constants for logged Team B runs:** Python 3.12.13, NVIDIA L4×4, docker digest `37c64f7…`, internet off, competition `gemma-4-developer-agent`, budgets 4.5 min / 50 tool calls / 50 turns.

## 6. Results (Team B only)

Artifact locations (worktrees; not committed):

| Run | Path / provenance |
|---|---|
| V1 diagnostic | `_wt-team-b-v1-kaggle-prep/.../smoke/20261123T063400Z` |
| V1 full smoke | `_wt-team-b-v1-kaggle-prep/.../smoke/20261123T073029Z` |
| V1 **dev** | **team-lead-reported** by Ashmitha (local Kaggle artifacts not available) |
| V2 diagnostic | `_wt-team-b-v2-kaggle-prep/.../smoke/20261123T084132Z` |
| V2 full smoke | `_wt-team-b-v2-kaggle-prep/.../smoke/20261124T070909Z` |
| V2 **dev** | `_wt-team-b-v2-kaggle-prep/.../dev/20261124T102323Z` (verified locally) |

| Variant | Commit | Diagnostic | Smoke | Dev (30) | Avg min/task (where verified) | Official Kaggle | Combined selection |
|---|---|---|---|---|---|---|---|
| Team B base (ref) | — | — | — | **7/30** (team-lead-reported) | — (no local artifacts) | — | selection baseline |
| `analyzer-plan` (V1) | `63a3eb2` | **1/2** | **0/10** | **5/30** (team-lead-reported) | diag **4.6**; smoke **4.3**; dev blank | **not confirmed** | **not selected** |
| `diff-critic` (V2) | `2cd4327` | **1/2** | **1/10** | **6/30** (local artifacts) | diag **4.6**; smoke **4.6**; dev **4.1** | **not confirmed** | **not selected** |

Averages are `mean(wall_seconds)/60` from each run’s `harness_results.jsonl` (one decimal). V1 **dev** and Team B base **dev** averages are blank because local Kaggle artifacts are unavailable.

**V2 dev breakdown (verified):** PASS 6 / FAIL 18 / EMPTY 6. Passing IDs: `fastapi_14077`, `fastapi_14301`, `fastapi_14492`, `rich_3278`, `rich_3718`, `rich_3905`.

**Smoke mechanism notes (unchanged):** V1 analyzer invoked 8/10 with 6 analyzer context-window failures; V2 critic invoked 1/10 with 0 completed feedback returns. Team A smoke reference for the budget agent (2/10) remains a labeled reference only.

## 7. Failure analysis and selection decision

### V1 — context overhead and timeouts
- Analyzer-first is often followed on smoke (8/10), but analyzer sessions frequently hit context limits.
- Dev **5/30** (team-lead-reported) is below Team B base **7/30** → **not selected** for the combined agent.

### V2 — critic under-used on smoke; modest dev gain still below base
- Smoke: critic rarely reached; the 1/10 resolve was not attributable to completed critic feedback.
- Dev **6/30** (verified) is still below Team B base **7/30** → **not selected** for the combined agent.
- Honest negative / null contribution for the multi-agent track under the fixed budget: neither intervention beat the Team B base on **dev**.

## 8. Risks, trade-offs, limitations

- Extra sub-agent calls spend turns/time inside 4.5 minutes → more timeouts (confirmed on smoke).
- Prompt-only policies may be ignored (V2 critic under-called on smoke).
- Critic `run_command` is not technically read-only; plain `git diff` misses untracked files.
- V1 **dev** lacks local Kaggle artifact provenance (team-lead-reported only).
- `run_info.git_rev` was dirty on several logged runs.
- **Dev ≠ official Kaggle.** Neither multi-agent variant has a confirmed official competition submission score in this log.

## 9. What remains

- Confirm whether any Team B **official Kaggle** submission uses a non–multi-agent combined agent (out of scope for this section’s scores).
- Keep PR #13 / #14 as implementation history; selection decision is documented here and in `docs/experiment_log.csv`.

## 10. References

3. Kon et al., SWE-Protégé, arXiv:2602.22124.
6. Zhao et al., Category-aware iterative expert training, arXiv:2609.23377.
11. Jiang, Lo and Liu, Agentic software issue resolution survey, arXiv:2512.22256.
