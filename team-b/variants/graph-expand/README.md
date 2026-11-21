**What changed:** added one skill, `skills/graph-expand/SKILL.md` (declared under `skills:` in `agent.yaml`): bounded graph expansion - seed symbol via `search_similar_code`, one hop of callers/callees/tests via `get_code_neighbors`, optional `get_code_subgraph`, capped at 4 graph calls and 6 symbols; everything else identical to `team-b/variants/base`.
**Why:** fixes that need a caller or callee changed together with the reported function (right file, wrong/incomplete fix), and wrong-file failures.
**Source:** [8] LARGER, [9] Codebase-Memory (graph context for repository-level code agents).
