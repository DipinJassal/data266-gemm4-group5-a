# Report section: Skills and tools (Poushali Deb Purkayastha)

*Draft for the group report.*

## Skills and tools

**Goal.** Submissions are declarative: no Python entry point and no custom tools, only the 9 harness tools, `agent_tool`
sub-agents and ADK skills (folders with a `SKILL.md`, loaded at run time with `load_skill`). This area tested whether
packaging practical know-how as a skill changes how the agent works within its 4.5-minute budget.

**Design.** The baseline error analysis showed three patterns: 23/30 dev patches changed no source file, 8/30 tasks had
malformed tool-call arguments, and no task ran the repository's own tests. V1 adds one skill, `fix-and-verify`, with
five rules: make the first source edit within 10 tool calls, use exact tool-call argument names (with examples), check
the fix by running only the related test file (`pytest -q -x --tb=short <file> | tail -25`) and treat missing test
dependencies as pre-existing, keep diffs small, and keep scratch scripts out of the patch. It deliberately avoids a
reproduce-first step, because Prompts V1 showed that pre-edit reproduction used up the budget. Team B found that this
model never loads a skill from its description alone [Team B, retrieval section], so the system prompt gets one line
telling the agent to call `load_skill` first. Everything else is the budget-fixed control (4.5 min, 50 tool calls).

**Results.**

| Run | Smoke | Avg min/task | Empty | Source edit made | Pre-edit Python runs |
|---|---|---|---|---|---|
| Control (Prompts RUN-006) | 1/10 | 4.67 | 2 | 5 | 9 |
| Skills pack, 2-task check | 2/2 | 4.4 | 0 | 2 | |
| **Skills pack, full smoke** | **1/10** | 4.6 | 6 | 2 | 22 |

The 2-task check found a wrong rule: the first version said "scratch files go in `/tmp`", but `write_file` only writes
inside `/workspace` and rejects `/tmp` as path traversal. The agent then wrote its script into the repository, where it
became part of the patch. The rule was changed to "scratch scripts only via `run_command` into `/tmp`" before the full
smoke run.

**What worked and what did not.** Loading worked: the agent called `load_skill` as its first action in 12 of 12 tasks.
Following did not. The agent broke the main rules often: 22 Python runs before the first edit against 9 in the control,
scratch scripts written into the repository in 3 tasks, and a source edit in only 2 tasks against 5. The one resolved
task is the one every variant resolves, and two `rich` tasks timed out in every variant because the model spent 35 to
91 seconds thinking between tool calls. With one 10-task run the resolved count (1 vs 1) is within noise, but the process
metrics point the wrong way, so no dev run was spent and V1 is a documented negative result.

**V2: test-runner sub-agent.** *(To be updated: not run yet at the time of writing.)*

**Takeaways.**
1. Skills are a cheap, valid way to ship know-how in a declarative submission, and a one-line trigger in the system
   prompt makes the model load them reliably.
2. Loading is not following: a multi-rule procedure read once at the start of the task does not reliably change what a
   quantized 31B model does several minutes later. Limits the harness enforces, such as the budget in `eval_config.yaml`,
   changed behaviour more than instructions did.
3. Tool constraints matter for instructions: telling the agent to use a path its tools cannot reach produced the very
   failure the rule was meant to prevent.

## Contribution-table row

| Member | Contribution |
|---|---|
| Poushali Deb Purkayastha | Skills and tools area: V1 skills pack (`fix-and-verify` skill and load trigger; 2-task check and full smoke, 1/10 vs control 1/10, a documented negative result with per-task analysis); found that `write_file` cannot write outside `/workspace`, so scratch scripts need `run_command`; confirmed the `load_skill` trigger works in 12/12 tasks; reviewed Bhoomika's LoRA V2 (leakage check, alpha and weights-access findings). |

## Slide (one slide)

**Title:** Skills and tools: can a skill teach the agent a better workflow?

- Submissions are declarative: 9 harness tools, sub-agents, and skills (`SKILL.md`, loaded with `load_skill`)
- V1 `fix-and-verify`: edit by call 10, exact tool arguments, run only related tests, no scratch files in the patch
- Loading works: one prompt line, `load_skill` first in **12/12** tasks
- Following does not: smoke **1/10** (control 1/10); source edits 2 vs 5, pre-edit runs 22 vs 9, empty patches 6 vs 2
- Found: `write_file` can't write `/tmp`, so scratch scripts need `run_command`
- Lesson: enforced limits change behaviour more than instructions read once at the start
