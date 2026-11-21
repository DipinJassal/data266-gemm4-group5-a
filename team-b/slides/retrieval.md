# Slide — Retrieval / code graph (Ishan)

**Title:** Find the right code fast: graph-first localization

- **Data (train, 99 tasks):** 71 % of fixes touch 1 file and 91 % touch ≤ 3; only 37 % of statements name the file or function; no tracebacks.
- **Problem:** the baseline spent its budget exploring; 23/30 dev patches changed no source file.
- **V1 graph-localize:** identifiers → `search_similar_code` → `get_code_neighbors` → read ≤ 3 files. Smoke TBD · dev TBD · Kaggle TBD
- **V2 graph-expand (skill):** one hop of callers, callees and tests, ≤ 4 graph calls and ≤ 6 symbols. Smoke TBD · dev TBD · Kaggle TBD
- **Lesson:** TBD (did the graph cut tool calls before the first edit? was the skill loaded?)

Chart: `team-b/docs/figures/eda_localization_signals.png`
