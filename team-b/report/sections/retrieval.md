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
| `graph-expand` (V2) | Adds one skill (`skills/graph-expand/SKILL.md`): seed symbol → one hop of callers, callees and tests → optional `get_code_subgraph`, capped at 4 graph calls and 6 symbols, ending in a 3-line edit plan. | Fixes that need a caller/callee change; incomplete fixes | [8] LARGER, [9] Codebase-Memory |

## Results

| Run | Split | Score | Avg min/task | Empty patches | Kaggle |
|---|---|---|---|---|---|
| base (Team A run) | smoke | 2/10 | 4.2 | 3 | — |
| graph-localize | smoke | TBD | TBD | TBD | — |
| graph-localize | dev | TBD | TBD | TBD | TBD |
| graph-expand | smoke | TBD | TBD | TBD | — |
| graph-expand | dev | TBD | TBD | TBD | TBD |

Dev scores are validation (used for selection); the Kaggle score is the held-out result.

## What worked, what didn't (to complete)

- Tool calls before the first edit, against base (from traces): TBD.
- Did the agent follow the routine (did it call `search_similar_code` first)? TBD.
- Did the skill get loaded (`load_skill` in traces)? If not, that's a documented negative result: a skill the model
  never loads changes nothing, so routing instructions belong in the system prompt.

## Limits and future work

- The localization statistics are lexical approximations; an offline file-hit@k check of the graph tools on train
  tasks was planned but not finished in time.
- The graph's symbol lookup expects symbol names. Short PR-title statements often contain none, which limits both variants.
- Future work: an analyzer sub-agent that runs the graph routine in its own context window and returns only the
  file list (combines with Parth's multi-agent design).
