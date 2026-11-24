# Retrieval and code-graph localization (Ishan, Team B) — first draft (Nov 21)

> Both Kaggle scores are in: graph-localize 0.12, graph-expand-2 0.08 (public leaderboard, one submission each).

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
| graph-localize | smoke (10) | 1/10 | 4.7 | 2 | **0.12** (public) |
| graph-expand | smoke, 2-task diagnostic | 2/2 | 4.2 | 0 | not submitted |
| graph-expand-2 | smoke, 2-task diagnostic | 1/2 | 4.4 | 0 | see smoke (10) row |
| graph-expand-2 | smoke (10) | 1/10 | 4.6 | 3 | **0.08** (public) |

The 2-task diagnostics run on the first two smoke tasks, which the base agent also solves, so they show that a variant
runs and follows its routine, **not** that it beats base. The full smoke runs and the Kaggle scores are the
comparison. We did not run dev: both variants scored 1/10 on smoke, and about 10 GPU-quota hours for two dev
runs would not change which variant goes into the combined agent. The Kaggle score is the held-out result: 0.12 for
graph-localize and 0.08 for graph-expand-2, one submission each, so the gap may be noise. No base Kaggle score is
recorded in the repo yet, so these do not show a gain or a loss against base.

## What worked, what didn't

- **graph-localize followed the routine partly.** On the 10-task smoke its first action was `search_similar_code` in
  9/10 tasks, but it called `get_code_neighbors` in only 1/10 and went straight to reading files.
- **Smoke: 1/10, no better than base** (base 2/10 in Team A's run, 1/10 in Khushi's matched control; n = 10, so
  these are within run-to-run noise). Two smoke tasks (fastapi_14962, requests_7505) cannot pass in this environment
  (missing test dependencies, Team A finding).
- **The bottleneck is time, not only finding the file.** 9/10 tasks hit the 4.5 min limit. In 5 of them the patch contains
  only a scratch reproduction script (`repro.py`, `reproduce_issue.py`) and no source edit: the agent spent its budget
  writing and running repro scripts after localizing. Faster localization alone does not help when the remaining
  budget goes to reproduction; the base prompt's "verify with a targeted test" step and the 4.5 min cap interact.
  This supports Ashmitha's patch-hygiene variant (scratch files) and points to "edit first, reproduce only if cheap"
  as future work.
- **Failed approach (G.3): a skill alone is not used.** In `graph-expand`, Kaggle's log confirms the skill toolset was
  enabled and the skill was shipped, but the model called `load_skill` in 0/2 tasks and used no graph tool. It behaved
  like base (2/2, same tasks base solves), so this run says nothing about graph expansion. Lesson: a skill's
  description alone does not trigger it for this model; the system prompt has to tell the agent to load it.
- **The trigger fixes activation, at a time cost.** `graph-expand-2` called `load_skill` then `search_similar_code` in
  2/2 tasks (and `get_code_neighbors` in 1/2). One task (fastapi_13537) then spent turns on scratch scripts and hit the
  4.5 min limit; base and graph-localize solve it. n = 2, so this is a warning sign, not a result.
- **Smoke: graph-expand-2 also 1/10.** The skill was loaded in 9/10 tasks and `get_code_neighbors` used in 4/10
  (vs 1/10 for graph-localize), but `get_code_subgraph` never. 9/10 tasks hit the time limit again; 4 patches contain
  only a scratch script and 3 are empty. More graph context did not turn into more fixes: the extra graph calls cost
  turns, and the agent still spent the rest of its budget on reproduction scripts.
- **Few tasks ever reach a source edit, and late.** From the 10-task smoke traces: only **3/10** tasks in each variant
  edited a non-test, non-scratch source file at all. When they did, the first source edit came after a median of
  **11 tool calls / 2.4 min** (graph-localize) and **14 calls / 2.8 min** (graph-expand-2), leaving under 2 minutes to
  test and submit. The other edits went to scratch scripts (`repro.py`, `reproduce_issue.py`) or nothing. The extra graph
  calls in graph-expand-2 pushed the first source edit later (about 3 more calls) without more tasks reaching one. Base
  traces from Team A's smoke run are not in our run folder, so this has no base comparison.

## Offline retrieval check (train, no GPU)

We re-implemented `search_similar_code` from the harness documentation (12/15 top-1 agreement with the real tool on
the agent's own calls) and ran one automatic query per train task (`team-b/docs/retrieval_eval.md`).

| | n | top-1 | top-5 (what the agent sees) | + neighbors of top hit |
|---|---|---|---|---|
| all train | 99 | 31% | **40%** | 42% |
| symbol query | 53 | 45% | 47% | 47% |
| keyword query (no symbol in issue) | 46 | 15% | 33% | 37% |
| fastapi / rich / requests | 52 / 37 / 10 | 17 / 38 / 80% | 21 / 57 / 80% | 23 / 59 / 80% |

The agent's own first search in the smoke traces reached a changed file in 9/17 tasks. So the graph localizes
about half the time (worse on fastapi, whose issue titles describe behaviour rather than the function to change),
and even when it did, the fix still did not land within the budget. Neighbor expansion adds little (2 points), which
matches graph-expand-2 not beating graph-localize. Test nodes fill 39% of the top-5 slots, but dropping them adds only
2 points: the query, not the ranking, is the main limit.

## Limits and future work

- The task EDA statistics are lexical approximations, and the retrieval check uses one regex-chosen query per task and
  a re-implemented search tool (file-level hits only).
- The graph's symbol lookup expects symbol names. Short PR-title statements often contain none, which limits both variants.
- Future work: an analyzer sub-agent that runs the graph routine in its own context window and returns only the
  file list (combines with Parth's multi-agent design).
