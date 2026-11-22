# Skills pack V1 (`poushali-skills-pack-v1`): smoke analysis

Owner: Poushali. Variant: `dipin-step-budget-v1` plus one skill, `skills/fix-and-verify/SKILL.md`, and one prompt line that tells the agent to load it first.
Control: Khushi's matched control run of `dipin-step-budget-v1` (RUN-006, `docs/v1_smoke_analysis.md`). Same 10 smoke tasks, same budget (4.5 min, 50 tool calls), 4x L4.

## Runs

| Run | Date (UTC) | Commit | Tasks | Resolved | Avg / max min | Notes |
|---|---|---|---|---|---|---|
| 2-task check | 2026-11-22 01:42 | `0bae175` | 2 | 2/2 | 4.4 / 4.7 | First two smoke tasks; not a score |
| Full smoke | 2026-11-22 02:41 | `08f7b70` | 10 | **1/10** | 4.6 / 5.8 | Run used the revised SKILL.md (hash checked in the kernel output) |

The 2-task check showed one wrong rule: the skill said "scratch files go in `/tmp`", but `write_file` only writes inside `/workspace`
(`Path traversal detected: '/tmp/repro.py' escapes workspace root`). The agent then wrote `reproduce_bug.py` into the repo and it ended up in
the patch. `08f7b70` changed the rule to "scratch scripts only via `run_command` into `/tmp`" and added "after 10 calls without an edit,
edit the most likely function now". The full smoke ran on that version.

## Full smoke vs control

| Task | Control (RUN-006) | Skills pack | Files in skills-pack patch | First source edit (call, s) | Pre-edit Python runs |
|---|---|---|---|---|---|
| `fastapi_11194` | failed (scratch only) | empty | none | none | 2 |
| `fastapi_13537` | **resolved** | **resolved** | `fastapi/dependencies/utils.py` | #8, 117 s | 1 |
| `fastapi_14609` | failed (source) | empty | none | none | 0 |
| `fastapi_14962` | failed (source)† | empty | none | none | 0 |
| `fastapi_15763` | failed (source) | empty | none (two root `test_*.py` scratch files, stripped as test files) | none | 4 |
| `requests_7505` | failed (source)† | failed (source) | `_types.py`, `models.py` | #9, 111 s | 0 |
| `rich_3180` | empty | empty | none | none | 2 |
| `rich_3506` | empty | empty | none | none | 1 |
| `rich_3782` | failed (scratch only) | failed (scratch only) | `reproduce_issue.py`, `_2`, `_3` | none | 4 |
| `rich_4075` | failed (scratch only) | failed (scratch only) | `repro.py` | none | 8 |

† Can't pass in this environment (missing test dependencies), see CLAUDE.md findings.

| Metric | Control | Skills pack |
|---|---:|---:|
| Resolved | 1 | 1 |
| Empty patch | 2 | 6 |
| Made a source edit | 5 | 2 |
| Scratch-only patch | 3 | 2 |
| Pre-edit Python runs, total | 9 | 22 |
| Skill loaded | n/a | 10/10 |
| Ran pytest | 1 | 1 |
| Avg / max time (min) | 4.67 / 5.78 | 4.6 / 5.8 |

## What it shows

- **Loading works.** With the trigger line, `load_skill("fix-and-verify")` was the first call in 12/12 tasks across both runs. This confirms Team B's finding from the other side: the trigger line is what makes the model load a skill.
- **Following does not.** The skill's three main rules were broken often: no reproduction script before editing (22 pre-edit Python runs vs 9), no scratch files via `write_file` (3 tasks), first edit by call 10 (only 2 tasks reached a source edit at all, vs 5 in the control).
- **Same tasks, same ceiling.** The one resolved task is the one every arm resolves. `rich_3180` and `rich_3506` are empty in every arm; in this run their median gap between tool calls was 35 s and 91 s (long thinking), so they time out with 4 to 10 calls regardless of instructions.
- **n = 10, one run.** Resolved is 1 vs 1, within run-to-run noise (the control itself scored 2/10 in Dipin's run). The process metrics point the wrong way, so this is not proposed for submission or the combined agent.

## Conclusion

Closed as a documented negative result (rule 7). A skill is a cheap, valid way to ship procedural know-how, and the load trigger is reliable,
but this 31B quantized model does not reliably follow a multi-rule procedure it loaded at the start once the task gets long. Hard limits
that the harness enforces (the budget in `eval_config.yaml`) or a smaller context per decision (an `agent_tool` sub-agent) are more likely to change behaviour than more instructions.
No dev run was spent.
