# Report section — Multi-agent (Parth Patel)

Team B · Group 5 · DATA 266 · Gemma 4 Developer Agent  
Status: **first draft (Nov 20, 2026)** — architectures implemented; smoke/dev/Kaggle numbers **pending**.

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

### Known limitations (pre-runtime)
- `run_command` is not technically read-only.
- Plain `git diff` misses untracked files; staged-only changes need `--cached` awareness.
- Effectiveness unmeasured until smoke traces are collected.

## 4. How each differs from the fixed base

| Aspect | Base | V1 | V2 |
|---|---|---|---|
| Analyzer registered | yes | yes (unchanged YAML) | yes (unchanged YAML) |
| Analyzer-first policy | no | **yes** | no |
| Critic sub-agent | no | no | **yes** |
| Budget / model / sampling | 4.5 / 50 / shared | same | same |

## 5. Evaluation methodology

Follow Team B split roles (`TEAM_B_GUIDE.md`):

| Split | Role | Cadence |
|---|---|---|
| smoke (10) | debug crashes, time, tool use | iterate |
| train (`--max-tasks 20`) | optional Phase-2 tuning | iterate |
| dev (30) | selection / validation | **one** run per finished candidate |
| Kaggle hidden | held-out | 1 submission/team/day |

Compare each variant to Team B base (and Team A reference smoke for the budget agent only as a labeled reference, never as our Kaggle score). Trace metrics of interest: analyzer/critic call rates, order relative to edits, revision rate, empty patches, wall time, tool calls, resolved tasks.

Launcher: Team B independent workflow (`team-b/kaggle/`, dataset `g5b-agents`, kernels `g5b-eval-*`) once adapters are restored.

## 6. Risks and trade-offs

- Extra sub-agent calls spend turns/time inside 4.5 minutes; risk of more timeouts or empty patches.
- Prompt-only policies may be ignored (seen in Team A time-awareness negatives).
- Critic false positives could cause harmful one-shot “fixes.”
- Cross-team GitHub sharing vs Kaggle private-sharing rules remains a process risk for the group; runtime evidence must stay attributed to Team B.

## 7. What remains untested

- Restored `adapter_model.safetensors` + `validate.py --zip`
- 2-task diagnostic and full 10-task smoke for V1 and V2
- Trace-level mechanism checks
- One-shot `dev` per finished candidate
- Team B Kaggle submission scores

## 8. Results (pending)

| Variant | Smoke resolved | Smoke avg min/task | Empty patches | Dev resolved | Kaggle | Notes |
|---|---|---|---|---|---|---|
| Team B base (ref) | pending / Team A smoke ref 2/10 @ 4.2 min labeled reference | — | — | — | — | Do not treat Team A numbers as Team B official |
| `analyzer-plan` | **pending** | **pending** | **pending** | **pending** | **pending** | PR draft; no GPU run yet |
| `diff-critic` | **pending** | **pending** | **pending** | **pending** | **pending** | PR draft; no GPU run yet |

## 9. References

3. Kon et al., SWE-Protégé, arXiv:2602.22124.  
6. Zhao et al., Category-aware iterative expert training, arXiv:2609.23377.  
11. Jiang, Lo and Liu, Agentic software issue resolution survey, arXiv:2512.22256.
