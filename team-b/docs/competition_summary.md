# Competition Summary — Gemma 4 Developer Agent (G.1)

Owner: Ashmitha · Team: GROUP_PROGRAMMING_05_b · Sources: Kaggle competition page, `data/HARNESS_README.md`

## Task
Build an autonomous software-engineering agent on Google's Gemma 4. For each task the agent receives a Python
repository and an issue (bug report or feature request), explores the code with tools, edits source files and
submits a patch. Kaggle applies the patch and runs hidden tests.

## Inputs (state)
- Repository snapshot inside an offline sandbox (`/workspace`), dependencies pre-installed.
- Issue text (problem statement).
- Pre-computed code graph and code embeddings, reachable through `get_code_neighbors`, `get_code_subgraph`
  and `search_similar_code`.

## Output (action)
- A patch (diff of source files) submitted with `submit_patch`. Unsubmitted edits at the time limit are also scored.

## Evaluation metric
- **Percentage of issues resolved**: a task counts only if the hidden tests pass after the patch is applied.
- Changes to test files and test configuration are stripped before scoring, so the fix must be in source code.
- Hidden tasks (~120) come from **private repositories**, not the 4 public ones (FastAPI, Rich, Requests, HTTPX).

## Submission format
- `submission.zip` with `agent.yaml` (or `root_agent.yaml`) at the root; declarative YAML, prompts and skills only.
- Allowed file types: `.yaml .yml .md .txt .py .json .safetensors`; no symlinks; nothing outside the root; < 3 GiB.
- Optional `eval_config.yaml` sets the per-task budget (`max_time_minutes`, `max_tool_calls`, `max_turns`).

## Agent components we can change
| Component | File(s) | Examples |
|---|---|---|
| System instructions | `prompts/system.md` | workflow, checklists, anti-looping |
| Sub-agents | `sub_agents/*.yaml` via `agent_tool` | analyzer, critic |
| Skills | `skills/<name>/SKILL.md` | reproduce-first, graph expansion |
| Sampling | `configs/sampling.yaml` | temperature, top-p, thinking budget |
| Budget | `eval_config.yaml` | time and tool-call limits |
| LoRA adapters | `adapters/*` (`.safetensors`, rank ≤ 128) | optional fine-tuning (Team A covers this) |

## Tools (only these 9, plus `agent_tool` sub-agents)
`run_command`, `submit_patch`, `get_status`, `read_file`, `edit_file`, `write_file`,
`get_code_neighbors`, `search_similar_code`, `get_code_subgraph`.

## Constraints
| Constraint | Value |
|---|---|
| Model | One base model per submission for all agents; we use `gemma-4-31b-it-qat-w4a16-ct` |
| Runtime | 12 hours for ~120 tasks, including sandbox setup → about 6 minutes per task |
| Context window | 32,768 tokens (`max_output_tokens`, `thinking_budget` ≤ 32,768) |
| Tool output caps (fixed by Kaggle) | 5,000 characters per command, 150 lines per `read_file` |
| Sandbox | Offline, 4 GiB RAM, 2 vCPUs |
| Submissions | 1 per team per day (day resets 4:00 pm Pacific); 2 final picks by Dec 2, 2026 |
| External data | Only what is inside the submission zip; no network in the sandbox |

## Local evaluation (how we score before submitting)
| Split | Tasks | Role |
|---|---|---|
| `smoke` | 10 (part of train) | Debugging |
| `train` | 99 | Tuning (Phase 2 uses the first 20) |
| `dev` | 30 | Selection (validation); one run per finished candidate |
| Kaggle hidden tasks | ~120 | Held-out test; the score we report |

## Compute we use
- Scored runs: Kaggle notebooks with L4 ×4 GPUs on each member's own weekly quota (L4 time counts double).
- No-GPU work (EDA, retrieval checks, charts, validation): Colab CPU runtime or laptops.

## Baseline
- Sample agent from the competition data, unchanged: 1 minute and 10 tool calls per task.
- Local dev score (Team A run, Nov 10): **2/30 = 6.7%**; 20 of 30 tasks produced no patch.
- Team B Kaggle baseline score: _fill in after the Nov 13 submission_.
