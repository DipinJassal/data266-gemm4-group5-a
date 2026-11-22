**What changed:** step 1 of `prompts/system.md` now localizes with the code graph first: pull identifiers from the issue, call `search_similar_code`, then `get_code_neighbors` on the top hit, and read at most 3 files (everything else identical to `team-b/variants/base`).
**Why:** wrong-file failures and time spent searching before the first edit (baseline: 23/30 dev patches changed no source file, many cut off while still exploring).
**Source:** [8] LARGER, [7] RepoAtlas (graph-based repository localization).
