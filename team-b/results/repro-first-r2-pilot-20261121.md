# Reproduce-first revision 2 pilot

Owner: Naveen. Run November 21, 2026, 20:02:03-20:19:51 UTC. Two smoke tasks only; not a full-smoke, dev, or official competition score.

## Results

| Measure | Initial pilot | Revision 2 |
|---|---:|---:|
| Resolved | 1/2 | 1/2 |
| Mean task wall time | 245.1 s (4.085 min) | 273.9 s (4.565 min) |
| Session timeouts | 1 | 1 |
| Empty patches | 0 | 1 |
| Scratch-only patches | 1 | 0 |
| Tasks that loaded the skill | 2/2 | 2/2 |

The same task passed and the same task failed in both pilots. R2 avoided scratch scripts in final patches, but did not improve resolution and averaged 28.8 seconds longer per task. These two-task observations do not establish a causal or statistically reliable performance change. See the [initial pilot](repro-first-pilot-20261121.md).

| Task | Resolved | Wall time | Patch and scoring evidence |
|---|---|---:|---|
| `fastapi_11194` | No | 276.6 s | Empty patch and session timeout. Scoring output empty; test exit code -1. |
| `fastapi_13537` | Yes | 271.2 s | Only `fastapi/dependencies/utils.py` changed; scoring reports two tests passed, exit 0. |

## Candidate and trace evidence

R2 changed only README, root prompt, and skill relative to PR #20's initial candidate at `cbee690660e5a88ca9bef8cdfc85e28b22b63407`. It requested inline checks without scratch scripts, uncaught assertions, one pre-edit and one identical post-edit execution, and immediate artifact cleanup. Model, adapters, sampling, analyzer, task splits, and budgets were unchanged. The runner was the same PR #15 snapshot except for run metadata. The unchanged repository validator, source-scope checks, skill metadata, and submission ZIP integrity checks passed before execution.

For `fastapi_11194`, the skill loaded at steps 3 and 34. Five inline reproduction attempts occurred at steps 4, 6, 7, 35, and 36; the separate version-printing command at step 5 is excluded. The first attempt passed; later attempts included assertion and syntax failures. Inspection continued until timeout. There was no source edit or submission call, and the patch is empty. Primary label: empty/invalid diff (empty); contributing flag: timeout. The one-pre-edit limit was not followed.

For `fastapi_13537`, the skill loaded at step 10. Four pre-edit attempts occurred at steps 11-14. Step 11 reports exit 0 with no output and does not establish reproduction; step 12 has a syntax error; step 13 prints the problematic value; step 14 raises an issue-related assertion with exit 1 (HTTP 422 instead of 200). Step 15 edits source at 217.6 seconds.

Three post-edit attempts followed at steps 16-18: a syntax failure, a passing check, and an extra check with a shell-quoting failure. Step 17 returns HTTP 200 with a null value and exit 0. Its assertions differ from the pre-edit command, so this was not the required identical rerun. Step 19 checks Git status and shows only the source file; step 20 submits at 252.9 seconds. Scoring reports two tests passed. No explicit diff-filename checks appear. The one-before/one-after policy was not followed; no complete checklist-compliance claim is justified.

Both traces use inline checks without scratch-script writes. Relevant failing assertions now return nonzero status, but repeated attempts, syntax/quoting errors, and delayed editing remain. Reported tool-call counts are 32 and 16; raw trace calls are 34 and 18. Keep these counting conventions separate.

## Provenance

- Output ZIP SHA-256: `701d32726793d511d4a689a138010621259c945c68ea423a25fbe2dae2fe11da`. CRC passed; exactly the expected two task summaries are present.
- Evidence root: `team-b__variants__repro-first/smoke/`; results use `run_info.json`, `harness_results.jsonl`, task details, final patches, and `swegemma/traces/trace_<task>.json`.
- Both captured root prompts and all returned skill bodies match the frozen R2 input bundle. This does not independently verify every uploaded byte or the runtime image digest.
- Recorded model: `gemma-4-31b-it-qat-w4a16-ct`; four GPUs. Budgets: 4.5 minutes, 50 calls, 50 turns, 60-second command timeout, 300-second verification timeout. vLLM startup: 429.5 seconds, excluded from mean task wall time.
- Run metadata records parent commit `cbee690660e5a88ca9bef8cdfc85e28b22b63407` with `dirty: true`: R2 ran from a local revised bundle before commit. Do not attribute the run to unchanged code at that parent.
- Input hashes: local `.review/naveen-build/repro-first-r2/manual-pilot-files.json`. Preserved output, summary, and tool timelines: `.review/naveen-build/pilot-r2-20261121/`. Raw traces and weights remain outside Git.

## Decision

Stop GPU evaluation for today and preserve the user's reported remaining quota (approximately five hours; not independently queried). Record R2 as a tested iteration, not a promoted improvement. Keep PR #20 draft. Full smoke, dev, and official submission remain pending. Plan further work against the remaining quota and persistent instruction-following/time-to-edit failures; do not automatically launch another run or raise budgets. Regression-check evaluation remains pending coordination with Poushali.
