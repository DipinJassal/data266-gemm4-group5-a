# Report section: Skills and tools (Poushali Deb Purkayastha)

*Draft for the group report.*

## Skills and tools

**Goal.** Submissions are declarative: no Python entry point and no custom tools, only the 9 harness tools, `agent_tool`
sub-agents and ADK skills (folders with a `SKILL.md`, loaded at run time with `load_skill`). This area tested whether
packaging practical know-how as a skill (V1) or as a sub-agent (V2) changes how the agent works within its 4.5-minute budget.

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

**V2: test-runner sub-agent.** V2 targets the same "no task ran the repository's tests" pattern with an `agent_tool`
instead of instructions. `test_runner_agent` may only use `run_command`, at most 3 times: it finds the tests related to
the change (`git diff --name-only` and `grep`), runs only those, and returns a 4-line report (`PASS`, `FAIL`, `BLOCKED`
for a missing test dependency, or `NO_TESTS`). With `skip_summarization`, the coder sees only those 4 lines, never the raw
test output. The baseline's own `code_analyzer` sub-agent was called in 0 of 12 traced tasks, so the system prompt again
gets a trigger line.

| Run | Trigger | Smoke | Avg min/task | Sub-agent called | Called, of tasks with a source edit |
|---|---|---|---|---|---|
| Control (Prompts RUN-006 / Dipin) | | 1/10, 2/10 | 4.67 | | |
| Test runner, iteration 1 | "after your source edit, call it" (step 3) | 2/10 | 4.4 | 0/10 | 0/5 |
| **Test runner, iteration 2** | "your next call after the first source edit must be it" | **1/10** | 4.4 | 1/10 | 1/4 |

When it was called (`fastapi_13537`), the sub-agent did exactly its job: 3 commands, a correct `PASS` from 13 related
tests, 15.5 seconds, and the coder submitted next, finishing in 2.9 minutes (the fastest run of that task in any variant).
In every other task the coder kept editing or went back to its own reproduction script, and in neither run did it ever run
pytest itself. The scores are within the control's own run-to-run range, so V2 is also a documented negative result, with
no dev run spent.

**Takeaways.**
1. Skills are a cheap, valid way to ship know-how in a declarative submission, and a one-line trigger in the system
   prompt makes the model load them reliably.
2. Loading is not following: a multi-rule procedure read once at the start of the task does not reliably change what a
   quantized 31B model does several minutes later. Limits the harness enforces, such as the budget in `eval_config.yaml`,
   changed behaviour more than instructions did.
3. Timing decides whether a trigger works: "your first action" got the skill loaded 12/12, while "after your edit" got
   the sub-agent called in only 1 of 9 tasks that made a source edit. The sub-agent itself was fast and correct.
4. Tool constraints matter for instructions: telling the agent to use a path its tools cannot reach produced the very
   failure the rule was meant to prevent.

## Contribution-table row

| Member | Contribution |
|---|---|
| Poushali Deb Purkayastha | Skills and tools area: V1 skills pack (`fix-and-verify` skill and load trigger; 2-task check and full smoke, 1/10 vs control 1/10, a documented negative result with per-task analysis); found that `write_file` cannot write outside `/workspace`, so scratch scripts need `run_command`; confirmed the `load_skill` trigger works in 12/12 tasks; V2 test-runner `agent_tool` (two smoke iterations, 2/10 and 1/10 vs control 1/10 and 2/10; sub-agent correct in 15.5 s when called but called in only 1 of 9 tasks with a source edit, a documented negative result); reviewed Bhoomika's LoRA V2 (leakage check, alpha and weights-access findings). |

## Slide (one slide)

**Title:** Skills and tools: can a skill or a sub-agent teach the agent a better workflow?

- Submissions are declarative: 9 harness tools, sub-agents, and skills (`SKILL.md`, loaded with `load_skill`)
- V1 `fix-and-verify`: edit by call 10, exact tool arguments, run only related tests, no scratch files in the patch
- Loading works: one prompt line, `load_skill` first in **12/12** tasks
- Following does not: smoke **1/10** (control 1/10); source edits 2 vs 5, pre-edit runs 22 vs 9, empty patches 6 vs 2
- Found: `write_file` can't write `/tmp`, so scratch scripts need `run_command`
- V2 `test_runner_agent`: runs only related tests, returns a 4-line PASS/FAIL/BLOCKED verdict
- Works when called (15.5 s, correct PASS, task done in 2.9 min), but called in only **1 of 9** tasks with an edit; smoke 2/10, 1/10
- Lesson: "first action" triggers work, "after X" triggers don't; enforced limits beat instructions
