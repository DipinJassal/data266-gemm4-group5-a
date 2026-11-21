**What changed:** same `skills/graph-expand` skill as `graph-expand`, plus one line in step 1 of `prompts/system.md` telling the agent to call `load_skill("graph-expand")` first (in `graph-expand` the skill was available but never loaded in 2/2 smoke tasks); everything else identical to `team-b/variants/base`.
**Why:** fixes that need a caller or callee changed together with the reported function, and wrong-file failures; the trigger line makes the agent actually use the skill.
**Source:** [8] LARGER, [9] Codebase-Memory (graph context for repository-level code agents).
