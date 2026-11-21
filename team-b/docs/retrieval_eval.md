# Offline retrieval check (Ishan) — OUTSTANDING

**Status:** not started; tracked here so it is not lost. Nothing below is a result yet.

**Goal:** measure, without a GPU, how often the graph tools point at the file the reference patch changes, so the
graph-first variants rest on a measured hit rate and not only on the task EDA.

**Plan (train split only, 99 tasks; dev is never used for tuning the matching):**
1. Load `graphs/<repo>.json` and `embeddings/<repo>.npz` from the competition data for each train task's repo snapshot.
2. From each problem statement, extract identifiers the way the `graph-localize` prompt tells the agent to (most
   specific symbol name first).
3. Reproduce `search_similar_code` offline (exact / suffix / case-insensitive / substring node match, then cosine
   similarity over the `.npz` vectors) and map each returned `node_name` to its file.
4. Report **file-hit@1 and file-hit@5** against the source files in the reference patch, overall and per repo,
   plus the share of tasks with no usable identifier (EDA: about 63 % of statements name neither file nor symbol).
5. Report dev once, after the matching is fixed.

**Owner / when:** Ishan, after the Kaggle submissions; it only feeds the report (G.2), not the agents.
