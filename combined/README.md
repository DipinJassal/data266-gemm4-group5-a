# Combined agent v1 (Dipin, Nov 23)

Team A (group 5a) changes only; nothing from `team-b/`. Base: `variants/dipin-step-budget-v1`.

| Part | Owner | From |
|---|---|---|
| Per-task budget, cut 4.5 → **4.0 min** / 50 calls (12-hour safety margin) | Dipin | `variants/dipin-step-budget-v1` |
| Structured loop: reproduce → localize → plan → edit → test → checklist | Khushi | `variants/khushi-structured-prompt-v1` |
| Keep tool output small (grep first, 60-line windows, capped output) | Dipin | `variants/dipin-output-trimming-v1` |
| At most one retry when the targeted check fails | Sarvesh | `variants/sarvesh-best-of-n-v2` |
| **New:** import check of changed modules, fix imports on rename, delete scratch files via `git status`, exact new-parameter names, "edit by ~30 calls" | Dipin | patch-hygiene check (combined-agent task) |

Left out: Bhoomika's LoRA (same 5/30 as the prompt-only variants; candidate for v2), Sarvesh's thinking-off (tie on smoke), Poushali's skills pack and test-runner tool (negative), Khushi's time-budget prompt (negative).

**Why the new checks.** In the `dipin-output-trimming-v1` dev run (5/30), the 25 unsolved tasks split into:
7 that can't pass in our harness (missing test packages), 3 whose patch broke the package on import
(`rich_4070` NameError: missing `import inspect`; `fastapi_14186` removed a name another module imports;
`fastapi_14262` didn't add the `scope` parameter the issue asks for), about 8 wrong fixes with 1–3 tests still failing,
5 empty patches (timeout before any edit), and scratch files (`repro.py`, `reproduce_issue.py`) in 11 patches.

**Sources:** [3] SWE-Protégé, [4] SWE-Master, [7] RepoAtlas, [9] Codebase-Memory, [11] Survey.
