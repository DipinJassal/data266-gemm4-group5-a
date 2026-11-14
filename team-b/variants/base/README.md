**What changed:** per-task budget in `eval_config.yaml`: 4.5 min and 50 tool calls (sample agent: 1 min, 10 tool calls); copied unchanged from Team A's `variants/dipin-step-budget-v1` at commit 93070c0.
**Why:** the sample agent's 1-minute cap cuts most tasks off before any edit (20/30 empty patches on dev); every Team B variant builds on this base.
**Source:** [3] SWE-Protégé (time and turn budget); Team A run data: smoke 2/10 at 4.2 min per task.
