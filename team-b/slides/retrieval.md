# Slide — Retrieval / code graph (Ishan)

**Title:** Find the right code fast: graph-first localization

- **Data (train, 99 tasks):** 71 % of fixes touch 1 file and 91 % touch ≤ 3; only 37 % of statements name the file or function; no tracebacks.
- **Problem:** the baseline spent its budget exploring; 23/30 dev patches changed no source file.
- **Offline check (train, no GPU):** one graph search reaches a changed file in **40 %** of tasks (rich 57 %, requests 80 %, fastapi 21 %); the agent's own first search on smoke: 9/17.
- **V1 graph-localize:** identifiers → `search_similar_code` → `get_code_neighbors` → read ≤ 3 files. Smoke 1/10 (base 1–2/10) · Dev 5/30 (base 7/30) · Kaggle 0.12 (base 0.10)
- **V2 graph-expand-2 (skill + trigger line):** one hop of callers, callees and tests, ≤ 4 graph calls. Smoke 1/10 · Dev not run · Kaggle 0.08 (base 0.10; one submission each, gaps may be noise)
- **Lessons:** (1) a skill is not used unless the system prompt says to load it (0/2 → 9/10); (2) finding the file is not enough: 9/10 smoke tasks still hit the 4.5 min limit, spent on repro scripts; (3) behaviour-style issue titles (fastapi) defeat symbol lookup.

Chart: `team-b/docs/figures/eda_localization_signals.png`
