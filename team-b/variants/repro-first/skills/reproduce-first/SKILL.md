---
name: reproduce-first
description: Reproduce the reported Python bug before changing source, rerun the same check after the fix, and remove the temporary reproduction before submitting. Use for each issue before the first source edit.
---

# Reproduce the reported bug

Use the issue's expected behavior to make one small, local assertion that distinguishes the bug from the fix. Keep time for source edits and submission.

## Before editing source

1. Read only the source needed to understand the reported behavior. Choose a new scratch filename under `/workspace`, outside test directories, that does not match `test_*.py` or `*_test.py`. Confirm it does not already exist; never overwrite an existing file. Remember the exact paths you create.
2. Write the smallest Python script that imports the affected project code and asserts the expected behavior. Avoid network access, large fixtures, new dependencies, and unrelated checks. Run it once with `python <scratch_file>` from the project root; ensure imports resolve to the workspace project.
3. A valid reproduction fails on the issue-related assertion or the reported exception. A syntax error, missing dependency, incorrect API use, import failure, timeout, or unrelated exception is not evidence that the issue was reproduced. If the scratch script itself is wrong, make at most one correction and rerun once. Do not weaken the expected behavior to obtain a failure or pass.
4. If reproduction is still unavailable, record why and proceed with the source fix using the issue and available code evidence. Do not install packages or alter repository tests/configuration to make the scratch script run. Never label this fallback as a successful reproduction.

## After editing source

5. Rerun the same reproduction with the same expected behavior. An issue-related failure before the edit and a pass afterward is evidence for the local fix, not proof that hidden tests will pass.
6. If the check still exposes the reported bug and budget remains, make at most one focused source correction and rerun. Otherwise keep the best source patch, state the check's actual result, and proceed to cleanup. Follow the root prompt's targeted-test rules; never run a full test suite.

## Before submitting

7. Remove only the scratch files created during this reproduction, including any scratch output you created. Do not delete pre-existing files, repository tests, or the source fix. Never use broad cleanup such as `git clean` or a wildcard delete.
8. Inspect `git status --short`, `git diff --name-only`, and `git diff --cached --name-only` to confirm those scratch paths are absent from tracked, staged, and untracked changes. Do not call `submit_patch` while your scratch files remain. Summarize whether reproduction was confirmed, the post-edit outcome, and any unavailable check.

Bound the work to at most two pre-edit reproduction executions and two post-edit executions. These are upper limits, not a requirement to consume them. When budget is tight, stop optional retries and prioritize cleanup and submission.
