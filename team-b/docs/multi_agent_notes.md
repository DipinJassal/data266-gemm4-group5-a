# Multi-agent notes (Parth) — how `agent_tool` sub-agents work in this competition

Sources: sample / Team B base `agent.yaml`, `harness/validate.py`, `harness/README.md`, `team-b/docs/competition_summary.md`.
These notes describe the **declarative** submission model (YAML only). They do not invent ADK APIs beyond what the harness and sample agent already use.

## 1. How sub-agents are declared

The root agent lists tools. Most tools are harness strings. A sub-agent is a mapping under `tools:`:

```yaml
- agent_tool:
    config_path: sub_agents/code_analyzer.yaml
    skip_summarization: true
```

- `config_path` is relative to the root `agent.yaml` and must stay inside the submission folder (`!include` / path escape rules in `validate.py`).
- Multiple `agent_tool` entries are allowed; `validate.py` walks every tool entry and recursively validates each referenced agent.
- The sample / Team B base already registers one analyzer this way. V2 adds a second critic `agent_tool` beside it.

## 2. Sub-agent config shape

Each `sub_agents/*.yaml` is itself an LLM agent config, same team model:

| Field | Role |
|---|---|
| `name` | Agent id the parent prompt refers to (e.g. `code_analyzer_agent`, `diff_critic_agent`) |
| `description` | Short capability text |
| `model` | Must be `gemma-4-31b-it-qat-w4a16-ct` (same as root) |
| `adapter` | Optional LoRA folder under `adapters/` (base uses `tool_lora` for sub-agents) |
| `instruction` | Usually `!include ../prompts/...` |
| `tools` | Subset of the 9 harness tools (or nested `agent_tool` — we do not nest further) |
| `generate_content_config` | Shared sampling include |

Root uses `main_lora`; analyzer/critic use `tool_lora` in the inherited base configs.

## 3. Prompt and response handoff

- Root `instruction` (`prompts/system.md`) decides **when** to call a sub-agent; the framework does not enforce call order.
- The parent passes a request string into the `agent_tool` call (issue text, pointers to inspect the workspace, etc.).
- With `skip_summarization: true`, the sub-agent’s full reply is returned to the parent (important for structured plans / critic problem lists).
- Sub-agent replies are **prompt contracts**, not typed schemas: V1 asks for ≤15-line Files/Root cause/Change/Uncertainty; V2 asks for `OK` or ≤3 problems.

## 4. Tool and context limitations

- Only the 9 harness tools + `agent_tool` are legal (`run_command`, `submit_patch`, `get_status`, `read_file`, `edit_file`, `write_file`, `get_code_neighbors`, `search_similar_code`, `get_code_subgraph`).
- Evaluation is offline; no network from the agent.
- Fixed caps (competition): command output ~5k chars; `read_file` ~150 lines; context 32,768 tokens.
- `get_status` is documented in Team A experiments as exposing wall-clock fields (`agent_elapsed_seconds`, `time_seconds_remaining`), **not** a full patch dump. Diff review therefore uses workspace inspection (`git diff` / `read_file`), not `get_status` alone.
- `run_command` is powerful: “read-only critic” is **prompt-enforced**, not sandbox-enforced.

## 5. Runtime and tool-call cost

- Each sub-agent call costs parent turns and wall time inside the per-task budget (`eval_config.yaml` on Team B base: `max_time_minutes: 4.5`, `max_tool_calls: 50`, `max_turns: 50`, `timeout_seconds: 60`).
- Analyzer or critic tool use also consumes the shared tool-call budget when the harness counts nested tool calls (measure on smoke traces; do not assume zero cost).
- Design implication: V1 adds a mandatory pre-edit call (+ optional one retry). V2 adds one post-edit call (+ optional one revision). Both trade localization/verification quality against the ~6 min/task team target.

## 6. Team B experiments that use this mechanism

| Variant | Branch / PR | Mechanism |
|---|---|---|
| `analyzer-plan` (V1) | `b/analyzer-plan` | Prompt policy on **existing** analyzer |
| `diff-critic` (V2) | `b/diff-critic` | New critic `agent_tool` + one revision |

Both copy `team-b/variants/base` and change only that one architectural intervention.

### Logged Team B scores (do not conflate splits)

| Variant | Diagnostic (2) | Smoke (10) | Dev (30) | Official Kaggle |
|---|---|---|---|---|
| Team B base (ref) | — | — | 7/30 (team-lead-reported) | — |
| `analyzer-plan` | 1/2 (`63a3eb2`) | 0/10 | 5/30 (team-lead-reported; local artifacts unavailable) | not confirmed |
| `diff-critic` | 1/2 (`2cd4327`) | 1/10 | 6/30 (verified run `20261124T102323Z`) | not confirmed |

Neither multi-agent variant was selected for the combined agent (both below base on **dev**). Dev ≠ official competition score.

Smoke mechanism summary: V1 analyzer invoked 8/10 with 6 analyzer context-window failures; V2 critic invoked 1/10 with 0 completed feedback returns. See `team-b/report/sections/multi-agent.md` and `docs/experiment_log.csv`.
