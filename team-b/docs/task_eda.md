# Task EDA (G.2) — Ishan, Team B

Notebook: `team-b/notebooks/task_eda.ipynb` (CPU only; runs on a laptop or Colab). Input: `data/tasks.jsonl`, the 129 public tasks.
Per-task table: `team-b/docs/task_eda_table.csv`. Charts: `team-b/docs/figures/eda_*.png`.

**Which tasks we used:** the design statistics below come from the **train split only (99 tasks)**, so nothing is
tuned on dev. The hidden Kaggle tasks come from private repos, so these numbers describe the *kind* of task,
not the exact repos.

## Findings and what we decided

| # | Finding (train, n = 99) | So we decided … |
|---|---|---|
| 1 | **71 % of fixes touch a single source file; 91 % touch ≤ 3.** Median fix: 12 changed lines in 2 hunks; 64 % change ≤ 20 lines. | The agent reads **at most 3 files** before editing (graph-localize step 1d), and graph-expand keeps at most 6 symbols. A wide search costs time and buys almost nothing. |
| 2 | **The problem statement rarely says where to look.** Only 21 % name a changed file and 23 % a changed function or class; 37 % have either. | The agent can't simply open the file named in the issue. It has to **search**, and the precomputed code graph (`search_similar_code` → `get_code_neighbors`) is the cheapest way to search in a 4.5-minute budget. This is the reason for both of Ishan's variants. |
| 3 | **Statements are short PR titles, not bug reports.** Median 48 words; 27 % under 20 words; 29 % are a title plus an issue link (e.g. "fix for markdown table / Fixes …/issues/3053"); **0 % contain a traceback**, 10 % a code block. | Prompts can't count on a stack trace to find the bug. The agent pulls **symbol names** out of the title (they're often the only clue) and passes them to `search_similar_code`, which expects a symbol name, not a sentence. |
| 4 | 8 % of reference patches **add a new source file**, and several are feature requests ("✨ Serialize JSON response …"), not bug fixes. | Prompts should say "implement the change", not only "fix the bug"; `write_file` stays enabled. (Note for Parth's category-routed idea.) |
| 5 | The public data is unbalanced: fastapi 67, rich 48, requests 13, httpx 1 (all 129). Localization signals differ by repo: rich names the file in 32 % of tasks, fastapi in 15 %. | No repo-specific rules (rule 4). Report per-repo dev scores next to the totals so one repo doesn't hide the effect. |

## Charts

- `figures/eda_tasks_per_repo.png`: public tasks per repo, split into train and dev.
- `figures/eda_fix_size.png`: source files changed per fix (left) and lines changed per fix (right).
- `figures/eda_localization_signals.png`: how often the issue names the file or function, or includes a traceback or code block.
- `figures/eda_issue_length.png`: problem-statement length in words.

## How it was measured (limits)

- "Source file" means any changed file that doesn't match a test pattern (`tests/`, `test_*.py`, `*_test.py`, `conftest.py`). Docs and scripts count as source.
- "Named in issue" means the full path, the file name, the dotted module path, or a distinctive file stem appears in the problem statement. "Function named" means a `def`/`class` name touched by the patch (from hunk headers and changed lines) appears as an identifier in the statement. Both are lexical approximations.
- Dev tasks (30) were excluded from every design statistic above.
