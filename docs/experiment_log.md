# Team experiment log (markdown mirror)

Canonical sheet may also live as `docs/experiment_log.xlsx` (Khushi). This file is the Sarvesh-updated mirror for runs we can commit without Excel.

| Run ID | Date (UTC) | Variant | Owner | One-line change | Smoke | Dev | Kaggle submit | Status | Notes |
|---|---|---|---|---|---|---|---|---|---|
| RUN-S01 | 2026-11-14 | `sarvesh-sampling-v1` | Sarvesh | thinking off (`thinking_budget: 0`); V2 budget 4.5 min / 50 calls | **2/10** | — | pending Nov 14 slot | smoke done | Ties `dipin-step-budget-v1` control (2/10). Max-2 check was 1/2. Logs: `docs/runs/sarvesh-sampling-v1-smoke-full-20261114T031152Z/` |
| RUN-D01 | 2026-11-22 | `dipin-output-trimming-v1` | Dipin | keep-tool-output-small prompt section on the V2 budget (4.5 min / 50 calls) | — | **5/30** | not submitted | dev done (PR #24) | Same 5 tasks as `khushi-structured-prompt-v1`. 5 empty, 1 context crash. Kernel `g5a-eval-variants-dipin-output-trimming-v1-dev`. |
| RUN-D02 | 2026-11-22 | `combined` v1 | Dipin | Team A merge: structured prompt + output trimming + single retry + import/scratch checks, 4.0 min | — | **4/30** | not submitted | **negative, closed** | 13 empty (vs 5); only 17/30 tasks reached an edit. Found `max_output_tokens` 16384 halves usable context. `docs/combined_v1_analysis.md`. |
| RUN-D03 | 2026-11-23 | `combined` v2 | Dipin | output-trimming prompt + `max_output_tokens` 8192 + one pre-submit import/scratch line, 4.5 min | — | **5/30** | not submitted | dev done | Same 5 tasks as the other 5/30 variants. Empty patches 2 (vs 5), context crashes 0 (vs 1), 17 timeouts. Kernel `g5a-eval-combined-dev` v2, git `34c1089`. |
| RUN-D04 | 2026-11-23 | `combined` v3 | Dipin | v2 + keep own messages short, never re-quote code or restate the issue | — | **5/30** | not submitted | no effect, closed | Same 5 tasks. Messages unchanged (141 vs 147 tokens/step, code re-quoting 18% both): the model ignored the rule; the trace text is likely its thinking (`include_thoughts: true`). 18 timeouts, 3 empty. git `f844aeb`. |
