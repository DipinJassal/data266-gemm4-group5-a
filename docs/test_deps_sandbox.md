# Grading all 30 dev tasks locally: `run_kaggle.py --test-deps`

*Dipin, Nov 27. Harness change on branch `dipin/test-deps-sandbox`. Checked in a CPU kernel; no GPU run yet.*

## Problem

In the default harness, 9 of 30 dev tasks fail test collection for every variant, the official reference patch included:

| Missing package | Tasks (base-v2 dev run, Nov 25) |
|---|---|
| `dirty_equals` | `fastapi_12942`, `fastapi_13713`, `fastapi_14303`, `fastapi_14356` |
| `inline_snapshot` | `fastapi_13207`, `fastapi_14186`, `fastapi_14246`, `fastapi_14262` |
| `pytest-httpbin` (fixture `httpbin`) | `requests_7433` (`docs/httpbin_investigation.md`) |

That's 8 fastapi tasks, not the 6 listed earlier: `fastapi_14186` and `fastapi_14262` also hit `inline_snapshot` in some test files.
So default dev scores are really out of **21** gradable tasks.

Cause (`docs/scoring_environment_comparison.md`): swegemma's subprocess sandbox skips `install_test_dependencies`, but it creates
each task's venv with `system_site_packages=True`, so it sees packages installed in the Kaggle kernel.

## Fix

`python harness/run_kaggle.py <variant> dev --test-deps`

- `harness/kaggle_runner.py` `install_test_deps()`, run right after the competition wheelhouse:
  `pip install --no-index --find-links <dataset> -c <constraints>` for `dirty-equals==0.9.0`, `inline-snapshot>=0.21.1,<0.32`,
  `pytest-httpbin==2.1.0`, `httpbin~=0.10.0`. Pins come from the repos (fastapi `requirements-tests.txt` / `pyproject.toml` at
  the dev tasks' base commits; requests `requirements-dev.txt`).
- The constraints file pins every package already installed (the first copy on `sys.path`, since the image has shadowed duplicates),
  so pip can only add packages. If the dataset is missing, the install fails or an import fails, the run stops: a run labelled
  `--test-deps` always has the packages.
- Wheels: private dataset `dipinjassal/g5a-test-deps` (27 Linux/CPython 3.12 wheels, 5.4 MB, readers: khushidonda, sarveshreshimwale,
  bhoomikalnu, poushali02). Rebuild with `harness/build_test_deps.sh`.
- Labelling: own kernel (`g5a-eval-<variant>-<split>-td`), `run_info.json["test_deps"]` holds the versions, and `summarize.py` prints them.

## Check (CPU kernel `dipinjassal/g5a-check-test-deps`, v2, same pinned image)

Wheelhouse install, then `install_test_deps()`: installed in 10 s (`dirty-equals 0.9.0`, `inline-snapshot 0.31.1`, `pytest-httpbin 2.1.0`,
`httpbin 0.10.4`). In a fresh `system_site_packages` venv (like a task sandbox), pytest on tests using `IsInt`/`IsStr`, `snapshot()` and the
`httpbin` fixture: **3 passed**. Unchanged afterwards: vllm 0.19.1, torch 2.10.0+cu128, swegemma 0.2.11, pytest 8.4.2, rich 13.9.4, flask 3.1.3.
v1 of the check stopped as designed (pip refused the install) because the constraints had picked the shadowed `six 1.16.0`;
fixed by keeping the first copy of each package.

## Caveats

- **Not comparable with earlier runs.** The agent sees the packages too, so it can run tests that used to error. Label results
  "test-deps harness" and re-run at least one existing variant (e.g. `dipin-base-v2`) with `--test-deps` as the new reference.
- **Not verified on a GPU run yet.** Dipin's weekly GPU quota is used up; the first `--test-deps` dev run needs someone else's quota.
- `pytest-httpbin` and `inline-snapshot` register as pytest plugins in every repo's test run. Neither changes results unless a test
  uses them; `httpbin` logs a harmless "flasgger is not installed" warning.
- Kaggle's official scorer (Docker path, private wheels cache) probably has these packages already; this brings our local grading closer to it, not past it.
