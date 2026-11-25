# budget-fit-2: budget-fit + 40 tool calls + two pre-submit checks

**Status:** built and validated, **not run** and not submitted. Do not submit before a dev run passes the gate below.

**What changed vs `variants/budget-fit`:**
- `eval_config.yaml`: `max_tool_calls` 28 -> **40** (8 min, 240 s, 80 turns unchanged).
- `prompts/system.md`: names in the issue must appear in the source exactly; before `submit_patch`, one `git grep` for those names and one `compile()` syntax check; call plan stretched to 40.

**Why:** in the budget-fit dev run (6/30) 13 of 30 tasks used all 28 calls, and one failure was a syntax error in the agent's own patch (fastapi_13713, duplicate argument). `compile()` is used because `ast.parse` does not catch that error and `py_compile` writes `.pyc` files.

**Limits of the evidence:** several failures call names the patch lacks (may_v1, endpoint_ctx, CellSpan, httpx.Stream), but those names do not appear in the issue text, so the name check cannot help them. Of that group only fastapi_14262 (`scope`) is named in the issue. Expected gain is small.

**Dev gate (set before the run):** resolved >= 7/30 and mean time per task <= 5.5 min (~120 hidden tasks inside 12 h).

## Results
Not run: the weekly Kaggle GPU quota on the account used for dev runs is spent until 2026-11-28 00:00 UTC. `harness/validate.py` OK and `run_kaggle.py --dry-run` structural checks pass.
