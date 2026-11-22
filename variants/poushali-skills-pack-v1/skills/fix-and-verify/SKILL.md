---
name: fix-and-verify
description: Load at the start of every task. Practical rules for getting a source edit in early, checking it with only the related repository tests, keeping the diff small, and leaving no scratch files in the patch.
---

# Fix and verify

The task budget is a few minutes. Most failed runs found the right file but ran out of time before editing it, or left a scratch script as the only change. Follow these rules.

## 1. Edit early

- Make the first edit to a source file within your first 10 tool calls. Read only the lines you need (`read_file` with `start_line` and `end_line`), then edit.
- If you have made 10 tool calls without an edit, stop exploring: edit the most likely function now with your best fix, then refine it.
- Do not write a reproduction script before editing. If you want a quick check of current behaviour, use one inline command: `python -c "..."`. Run it at most once before the edit.
- A plausible fix that is submitted beats a perfect fix that is cut off. An unsubmitted diff is still scored, but an empty diff always fails.

## 2. Call tools with exact argument names

- `read_file(filepath="pkg/module.py", start_line=40, end_line=120)`
- `edit_file(filepath="pkg/module.py", old_string="<exact existing text>", new_string="<replacement>")`
- `run_command(command="...")`
- Copy `old_string` exactly from what `read_file` returned, including indentation. Keep it to the few lines you change plus one line of context so it matches once.
- If an `edit_file` call fails, read those lines again and retry once with a smaller `old_string`. Do not repeat the same failing call.

## 3. Verify with the related tests only

1. Find the test file that covers the code you changed:
   `grep -rl "<function_or_class_name>" tests test 2>/dev/null | head -5`
2. Run only that file, quietly, and keep the output short:
   `python -m pytest -q -x --tb=short -p no:cacheprovider <test_file> 2>&1 | tail -25`
   Add `-k <name>` to narrow it to the relevant tests when the file is large.
3. Read the result:
   - All pass: submit.
   - A failure in the behaviour you changed: fix the source once more, rerun the same command once, then submit.
   - `ModuleNotFoundError`, `ImportError` or errors during collection for a package you did not touch: the test environment is missing a dependency. This is not your bug. Do not install anything or edit tests. Run one inline `python -c` check of your change instead, then submit.
   - Failures in tests unrelated to your change: ignore them and submit.
4. Never run the whole suite (bare `pytest`, `pytest .`, `pytest tests/`). Never edit or create test files; they are removed before scoring.

## 4. Keep the diff small

- Change only what the issue needs. No renames, reformatting or unrelated cleanup.
- Keep each `edit_file` small. Several small edits are safer than one large one.
- Never modify `pytest.ini`, `conftest.py`, `pyproject.toml`, `setup.cfg` or `tox.ini`.

## 5. Clean up, then submit

- Never create scratch files with `write_file` or `edit_file`: those tools only write inside `/workspace`, and anything new there becomes part of your patch. If you need a scratch script, create it in `/tmp` with `run_command`, for example `run_command(command="cat > /tmp/check.py <<'EOF'\n...\nEOF\npython /tmp/check.py")`.
- Before submitting, run `git status --short` once. Delete any file you created that is not part of the fix (for example `rm repro.py`). Never delete files that existed before you started.
- Call `submit_patch` last, and check that `files_changed` is at least 1.
