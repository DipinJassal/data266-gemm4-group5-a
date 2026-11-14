# `requests` tasks and the missing `httpbin` test fixture

*Investigation by Khushi, Nov 14. CPU only; no GPU runs and no changes to the harness or any variant.*

## Summary

`requests_7505` (smoke) scored **142 passed, 0 failed, 197 errors** in Phase 2. Every error is
`recursive dependency involving fixture 'httpbin' detected`. The requests repo needs the `pytest-httpbin` plugin, and the
test environment doesn't have it. In a local reproduction of the sandbox, the **official reference patch gets the same 197 errors**. So in this
environment, as reproduced locally and as seen in our Kaggle swegemma runs, the task can't be resolved whatever patch an agent writes.

**Scope:** 8 of the 13 public `requests` tasks run their hidden tests in `tests/test_requests.py`, which uses the fixture
throughout. That includes smoke `requests_7505` and **dev `requests_7433`**. The same failure is likely for all 8;
only `requests_7505` was checked directly.

## Evidence

| # | Check | Result |
|---|---|---|
| 1 | Kaggle Phase 2 output for `requests_7505` (V1 smoke run, Nov 14, `task_details/requests_7505.json`) | 142 passed, 1 skipped, 1 xfailed, 197 errors. All 197 are `httpbin`/`httpbin_secure` recursive-fixture errors. pytest's "available fixtures" list has only built-ins and the repo's own conftest fixtures: no plugin fixtures. The target test `test_post_getattr_proxy_read_only` is one of the errors. |
| 2 | Why the fixture is recursive | `tests/conftest.py:34` defines `def httpbin(httpbin):`, a wrapper around the fixture that `pytest-httpbin` should supply. Without the plugin, the fixture refers to itself. |
| 3 | Does the repo declare the dependency? | Yes. `requirements-dev.txt` lists `pytest-httpbin==2.1.0` and `httpbin~=0.10.0`, and pyproject's `[dependency-groups] test` does too. |
| 4 | Is it in the competition environment? | No. The 124 competition wheels include `flask` and `werkzeug`, but **not** `pytest-httpbin` or `httpbin`. `sandbox/setup.py` installs only declared packages found in `/wheels`, and `docker/Dockerfile.sandbox` installs `pytest`, `pytest-timeout` and build tools only. The sandbox is offline (`network_mode="none"`). |
| 5 | Local offline reproduction, **calibration**: V1's actual agent patch | 142 passed, 1 skipped, 1 xfailed, **197 errors**. Same as Kaggle. |
| 6 | Local reproduction, **no agent patch** | 142 passed, 1 skipped, 1 xfailed, **197 errors**; the target test errors. |
| 7 | Local reproduction, **official reference patch** | 142 passed, 1 skipped, 1 xfailed, **197 errors**; the target test errors. **Not resolvable.** |
| 8 | Counterfactual: `pytest-httpbin` installed in a separate throwaway venv (not the experiment environment) | Reference patch: **339 passed, 0 errors** (would resolve). No patch: the target test **fails**, so it's a genuine fail-to-pass test. |

**Local reproduction method** (a local diagnostic script, not committed):
- the official snapshot `snapshots/requests_7505.tgz`
- Python 3.13, the same version as `Dockerfile.sandbox`
- a fresh venv per case, installed with `pip --no-index` from the competition wheels only
- the official `sandbox/setup.py` fast path (writes `pytest.ini` and the conftest hook)
- a baseline commit, then the patch, a test-file reset and `test_patch`, as in HARNESS_README §8.2
- the exact §8.2 pytest command

The resolution rule requires `errors == 0`, so any `httpbin` error fails the task.

## Affected tasks (from `tasks.jsonl`; file-level only)

| Hidden tests in | Tasks | Split |
|---|---|---|
| `tests/test_requests.py` (uses `httpbin`) | `requests_7505` | smoke (smoke is a subset of train) |
| | `requests_7433` | **dev** |
| | `requests_7502`, `requests_7328`, `requests_6757`, `requests_6629`, `requests_6589`, `requests_6592` | train |
| `tests/test_utils.py` or `tests/test_adapters.py` (no `httpbin` fixture in the 7505 snapshot) | `requests_7427`, `requests_7315` (dev); `requests_7309`, `requests_7205`, `requests_6644` (train) | likely unaffected |

## Limitations (not verified)

- **Kaggle's official Stage 2 scorer was not run.** Our Kaggle runs used swegemma's subprocess sandbox (paths `/tmp/swegemma_sandbox_…`). The official scorer uses the Docker backend plus "cached test site-packages" that aren't published. If that cache includes `pytest-httpbin`, official scoring could differ. Nothing published suggests it does.
- Only the `requests_7505` snapshot was tested. The other 7 tasks are inferred from which test file their hidden tests target. `requests_7433` (dev) was deliberately not run, to keep dev held out.
- The local reproduction is an approximation of Container B: macOS with a venv, not the Linux image, and not network-isolated. It matched the Kaggle result exactly (#5).

## What this means for us

- Report `requests_7505` in every smoke comparison, and also give the result **excluding** it as a sensitivity check. Never drop it silently.
- **If** the official scorer behaves like our sandbox, dev `requests_7433` can't be resolved by any variant, including the baseline. That's an
  inference, not a measured ceiling. It may partly explain the baseline's 0/3 on requests, though that run has no Phase 2 output to confirm it.
- A harness or environment fix (for example, providing `pytest-httpbin`) isn't ours to make. This is reported, not fixed.
