# Offline retrieval check (Ishan, Team B)

**Question:** how often do the graph tools point at a file that the reference patch changes? Measured offline (no
GPU) on the 99 **train** tasks; dev was not used. Script: `team-b/analysis/retrieval_eval.py`; per-task table:
`team-b/docs/retrieval_eval_table.csv`.

## Method

1. For each train task, load the competition's `graphs/<repo>_<commit>.json` and `embeddings/<repo>_<commit>.npz`
   for that task's snapshot (97 snapshots, 663 MB, git-ignored).
2. Pick one query from the problem statement, as step 1a–1b of `graph-localize` tells the agent: the most specific
   identifier that resolves to a graph node (dotted name → backticked name → CamelCase → snake_case → `name(`);
   if none resolves, 3 keywords.
3. Re-implement `search_similar_code` from `HARNESS_README` §6.3: 4-tier name resolution (exact → suffix →
   case-insensitive → substring), then cosine similarity over the `.npz` vectors, with the resolved node itself left out
   of the results (as in the real traces); a token-overlap fallback for keyword queries.
   **Fidelity check:** my top-1 equals the top-1 Kaggle returned in **12/15** real agent calls (the keyword fallback
   and tie-breaking are not documented, so this is an approximation).
4. A result node "hits" when its dotted module path is a source file the reference patch changes (test files excluded).

Metrics: **seed** = the query itself resolves into a changed file; **hit@k** = one of the top-k results is in a changed
file; **s|h@k** = seed or hit@k (what the agent actually sees); **+nbrs** = s|h@5 or a neighbor of the top hit
(graph-localize step 1c); **noTest** = s|h@5 after dropping test nodes from the results.

## Results (train, n = 99)

| Group | n | seed | hit@1 | hit@5 | hit@10 | s\|h@1 | s\|h@5 | +nbrs | noTest | test nodes in top 5 |
|---|---|---|---|---|---|---|---|---|---|---|
| **all** | 99 | 22% | 24% | 33% | 38% | 31% | **40%** | 42% | 42% | 39% |
| symbol query | 53 | 42% | 32% | 34% | 40% | 45% | 47% | 47% | 47% | 39% |
| keyword query | 46 | 0% | 15% | 33% | 37% | 15% | 33% | 37% | 37% | 39% |
| fastapi | 52 | 13% | 13% | 17% | 23% | 17% | **21%** | 23% | 23% | 45% |
| requests | 10 | 60% | 40% | 40% | 50% | 80% | 80% | 80% | 80% | 46% |
| rich | 37 | 24% | 35% | 54% | 57% | 38% | 57% | 59% | 59% | 29% |

(The only httpx task is in dev, so httpx is not in this table.) The changed module exists in the graph for 94/99 tasks,
so misses are retrieval misses, not missing data.

**The agent's own queries** (first `search_similar_code` call in each smoke trace of graph-localize and graph-expand-2,
latest run per task, n = 17): the query resolved into a changed file in 10/17, top-1 hit 7/17, top-5 hit **9/17**.

## What it means

- **The graph finds the right file in about 4 of 10 tasks** (40% within what the agent sees after one search;
  one hop of neighbors adds only 2 points). It is far better on rich (57%) and requests (80%) than on fastapi (21%).
- **fastapi is the weak spot.** 50/52 fastapi train fixes are in library code, many in `fastapi/dependencies/utils.py`,
  but the issue titles describe behaviour (`File` after `Form`, stringified annotations) rather than the function to
  change. The query then resolves to the user-facing class (`fastapi.params.File`), and its embedding neighbours are
  other parameter classes or test functions, not the parsing code. fastapi is 52% of train, so this drags the
  overall rate down.
- **Test nodes take 39% of the top-5 slots**, but dropping them adds only 2 points: test crowding is not the main
  failure; the query choice is.
- **Symbol queries work better than keyword queries** (47% vs 33%), which supports the prompt's "use a symbol name,
  not a sentence" rule. But 46% of statements give no resolvable symbol at all.
- **Link to the smoke results:** in the smoke runs the agent's first search reached a changed file in 9/17 tasks, yet
  both variants solved 1/10. So retrieval is only part of the problem: finding the file is necessary but did not
  turn into fixes within the 4.5 min budget (see `team-b/report/sections/retrieval.md`).

## Limits

- One automatic query per task; the real agent may search twice and reads the issue more cleverly than a regex.
- `search_similar_code` is re-implemented (12/15 top-1 agreement), not the official code.
- File-level hits only; a hit does not mean the agent reads the right function.
- Train only, by design; dev is not reported, because no tuning decision depends on this check.

## Reproduce

```
kaggle competitions download gemma-4-developer-agent -f graphs/<key>.json -p ../graphdata/graphs     # and embeddings/<key>.npz
python team-b/analysis/retrieval_eval.py --data ../graphdata --split train --traces harness/runs
```
`<key>` = `<repo short name>_<base_commit>` for each train task.
