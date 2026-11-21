---
name: graph-expand
description: Load this at the start of every task, before reading files. Bounded code-graph expansion - finds the symbol the issue is about, then its callers, callees and related tests with at most 4 graph tool calls, so you edit the right function (and its caller/callee when the fix needs it).
---

# Graph expansion (bounded)

Use the repository's code graph to see the code around the bug before you edit. Spend **at most 4 graph
tool calls** in total (`search_similar_code`, `get_code_neighbors`, `get_code_subgraph`), then move on.

## Steps

1. **Seed symbol.** From the issue text pick the most specific symbol name: a function, method or class
   (`"Class.method"`, `"parse_header"`, `"pkg.module.func"`). Pass a symbol name, not a sentence.
   If the issue names none, use 2–3 keywords from the error message.
2. **Find it.** `search_similar_code(query=<seed>, k=5)`. Take the top 1–2 `node_name`s that are source
   code (skip anything under `tests/`, `docs/` or examples unless the issue is about them).
3. **Expand one hop.** `get_code_neighbors(node=<top node>, max_neighbors=15)`. From the neighbors keep at
   most **6** symbols: up to 3 callers, up to 2 callees, and 1 test function whose name matches the symbol
   (e.g. `test_<name>`), if one is listed.
4. **Connect (optional).** Only if the fix might span two of the kept symbols, call
   `get_code_subgraph(nodes=[...])` with the top node plus those (max 6 nodes) to see which calls connect them.
5. **Decide the edit set.** Write down, in 3 lines or less: the function you will change, any caller or
   callee that must change with it, and the test file to run. The dotted path of a node gives its file
   (`pkg.sub.module.Class.method` -> `pkg/sub/module.py`).
6. **Read only those.** Use `read_file` with line ranges on at most 3 files from the edit set, then edit.

## Rules

- Never exceed 4 graph tool calls or 6 kept symbols; the graph is for finding code, not for reading it.
- If a graph tool returns an error or nothing useful, stop using the graph and fall back to the
  file paths and names in the issue.
- Test functions are only for choosing which test file to run. Never edit test files.
