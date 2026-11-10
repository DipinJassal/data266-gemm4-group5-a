**What changed:** per-task budget in `eval_config.yaml`: 4.5 min and 50 tool calls (baseline: 1 min, 10 tool calls); nothing else.
**Why:** the baseline's 1-minute / 10-call cap cuts most tasks off before an edit (timeout / empty-diff failures); 4.5 min fits 120 tasks in 12 h with setup.
**Source:** TODO Dipin: pick reference number from CLAUDE.md
