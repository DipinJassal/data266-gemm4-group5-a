---
name: reproduce-first
description: Run one inline Python reproduction before changing source and the same check after the fix, with uncaught assertions and no scratch scripts. Use before the first source edit; if reproduction is unavailable, proceed with the source fix.
---

# Reproduce the reported bug

Use one small assertion of the issue's expected behavior. At most one pre-edit execution and one post-edit execution; no reproduction retries or replacement checks. Keep time for the source fix and submission.

## Before editing source

1. Read only the source needed to identify the likely fix and a minimal check. Use the project's interpreter from the repository root so imports resolve to workspace source. Run Python with `-B` and inline code (`-c` or standard input); do not create a reproduction script or test file. Avoid checks that write persistent files, need network access, new dependencies, large fixtures, or long-running services.
2. Execute the check once. Assert the expected behavior directly: let an assertion or unexpected exception propagate and produce a nonzero process exit. Do not catch and print failures while returning success, use `python -O`, or mask the exit status with a later shell command.
3. Classify the result using both the exit status and output. Only a nonzero exit caused by the issue-related assertion or reported exception confirms reproduction. A pass before editing means the bug was not reproduced; an import, syntax, API-use, dependency, or timeout failure is blocked evidence. Do not change the assertion to manufacture a failure.
4. Whether reproduced, already passing, blocked, or impractical, move directly to the source fix using the issue and code evidence. Do not repair the check, try another check, install packages, or alter tests/configuration. If no suitable inline check is available, skip it and state why. If execution unexpectedly created an artifact, remove only that artifact immediately before further work; never overwrite or delete pre-existing files.

## After editing source

5. If the pre-edit check confirmed reproduction and time remains, execute the identical inline command once after the source fix. Preserve the inputs and assertions. A meaningful pre-edit failure followed by exit 0 with no failure output supports the local fix; it does not prove hidden tests will pass. If the pre-edit check was blocked, passed, or skipped, do not spend another execution on it or claim fail-to-pass verification.
6. Record the actual post-edit result, including a remaining failure or a skipped check. Do not enter a reproduction-driven repair loop. Immediately remove only unexpected artifacts created by your check. Follow the root prompt's targeted-test rules, never full-suite runs; under time pressure prioritize a source patch and submission over additional verification.

## Before submitting

7. Inspect `git status --short`, `git diff --name-only`, and `git diff --cached --name-only` in one tool call. Confirm the patch contains the intended source fix and no artifacts from your check. Remove only artifacts you created, never pre-existing files, repository tests, or source changes; do not use `git clean` or wildcard deletion.
8. Submit promptly and summarize the pre-edit result, post-edit result, and any unavailable verification accurately. Do not describe an unexecuted, blocked, or failing check as passing.
