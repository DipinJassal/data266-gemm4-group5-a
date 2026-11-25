**What changed:** combined v2 (5/30, fewest empty patches) with a 7 min / 50 calls / 80 turns budget (was 4.5 min / 50 / 50), a short budget section in the prompt (the working tree is graded when time runs out; edit by about call 15), `git grep` instead of the graph tools for locating code, and a one-word exit after `submit_patch`.
**Why:** in combined v2's dev run 17/30 tasks were cut off at 4.5 min, most after they had already edited; every solved task made its first edit by tool call 13; graph-tool calls mostly came back empty (3 of 5 in output trimming).
**Source:** [3] SWE-Protégé (small models stall; explicit budgets help), [12] SWE-bench.

**Dev result (Nov 25, git `83fa423`): 6/30 = 20.0%** (fastapi 4/15, rich 2/11). The usual 5 tasks plus `fastapi_14616`, solved at 7.1 min (past the old 4.5 min cap). Time-outs 10 (vs 17 for combined v2), empty patches 1, no crashes; avg 5.1 min, max 7.2 min per task.
