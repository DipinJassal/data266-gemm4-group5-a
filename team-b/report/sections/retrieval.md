# Retrieval and code-graph localization (Ishan, Team B) — DRAFT

> Fill the `TBD` cells from `team-b/docs/experiment_log.csv` once the smoke, dev and Kaggle runs are in.

## Task analysis (G.2)

We analysed the 99 public **train** tasks (dev excluded) to decide how the agent should find the code to change
(`team-b/docs/task_eda.md`). Three findings shaped the design:

1. **Fixes are small.** 71 % change one source file and 91 % change at most three; the median fix is 12 lines.
2. **The problem statement rarely says where to look.** Only 37 % name a changed file or a changed function/class.
3. **Statements are short PR titles, not bug reports.** Median 48 words, no tracebacks, and 29 % are a title plus an issue link.

So the agent has to *search*, and the search must be cheap: about 4.5 minutes per task, with roughly 7 s
per tool call (Team A's baseline profile). The competition ships a precomputed call graph and code embeddings for
every repo. Both variants use them in place of `find`/`grep` exploration, which in the baseline used up the time
budget before the first edit (23/30 dev patches changed no source file).

## Variants (one change each from `team-b/variants/base`)

| Variant | Change | Targets | Source |
|---|---|---|---|
| `graph-localize` (V1) | Step 1 of the system prompt becomes a fixed localization routine: pull up to 5 identifiers from the issue → `search_similar_code` with one symbol name → `get_code_neighbors` on the top hit → read at most 3 files. | Wrong-file failures; time spent searching before the first edit | [8] LARGER, [7] RepoAtlas |
| `graph-expand` (V2, **failed skill invocation**) | Adds one skill (`skills/graph-expand/SKILL.md`): seed symbol → one hop of callers, callees and tests → optional `get_code_subgraph`, capped at 4 graph calls and 6 symbols, ending in a 3-line edit plan. **Not an evaluated graph-expansion strategy:** the skill was available but never loaded (see below). | Fixes that need a caller/callee change; incomplete fixes | [8] LARGER, [9] Codebase-Memory |
| `graph-expand-2` (V2, evaluated) | Same skill + one line at the top of step 1 of the system prompt: "Your very first action must be `load_skill` with `skill_name="graph-expand"`". | Same as above | [8], [9] |

## Results

| Run | Split | Score | Avg min/task | Empty patches | Kaggle |
|---|---|---|---|---|---|
| base (Team A run) | smoke | 2/10 | 4.2 | 3 | — |
| graph-localize | smoke, 2-task diagnostic | 2/2 | 4.1 | 0 | — |
| graph-localize | smoke (10) / dev | TBD | TBD | TBD | pending (submitted Nov 21) |
| graph-expand | smoke, 2-task diagnostic | 2/2 | 4.2 | 0 | not submitted |
| graph-expand-2 | smoke, 2-task diagnostic | 1/2 | 4.4 | 0 | TBD |
| graph-expand-2 | smoke (10) / dev | TBD | TBD | TBD | TBD |

The 2-task diagnostics run on the first two smoke tasks, which the base agent also solves, so they show that a variant
runs and follows its routine, **not** that it beats base. Comparative claims wait for the full smoke/dev runs and
the Kaggle scores. Dev scores are validation (used for selection); the Kaggle score is the held-out result.

## What worked, what didn't

- **graph-localize followed the routine partly.** Its first action was `search_similar_code` in 2/2 tasks, but it
  skipped `get_code_neighbors` and went straight to reading files.
- **Failed approach (G.3): a skill alone is not used.** In `graph-expand`, Kaggle's log confirms the skill toolset was
  enabled and the skill was shipped, but the model called `load_skill` in 0/2 tasks and used no graph tool. It behaved
  like base (2/2, same tasks base solves), so this run says nothing about graph expansion. Lesson: a skill's
  description alone does not trigger it for this model; the system prompt has to tell the agent to load it.
- **The trigger fixes activation, at a time cost.** `graph-expand-2` called `load_skill` then `search_similar_code` in
  2/2 tasks (and `get_code_neighbors` in 1/2). One task (fastapi_13537) then spent turns on scratch scripts and hit the
  4.5 min limit; base and graph-localize solve it. n = 2, so this is a warning sign, not a result.
- Tool calls before the first edit, against base: TBD (needs the full smoke traces).

## Limits and future work

- The localization statistics are lexical approximations. **Outstanding:** the train-only offline retrieval check
  (`team-b/docs/retrieval_eval.md`, file-hit@1/@5 of the graph tools against the reference patches) is planned but
  not done yet.
- The graph's symbol lookup expects symbol names. Short PR-title statements often contain none, which limits both variants.
- Future work: an analyzer sub-agent that runs the graph routine in its own context window and returns only the
  file list (combines with Parth's multi-agent design).
