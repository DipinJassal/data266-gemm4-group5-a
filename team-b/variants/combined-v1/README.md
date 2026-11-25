# combined-v1: base + per-turn token caps

**What changed:** `configs/sampling.yaml` only. `max_output_tokens` 16384 -> 3072 and `thinking_budget` 4096 -> 1024. Prompt, tools, sub-agents and `eval_config.yaml` (4.5 min, 50 tool calls) are identical to `variants/base`.

**Why:** in the base dev traces the model decodes at about 30 tokens/s and generation is about 80% of each task's wall time. Single long turns (2,000 to 7,850 tokens, 1 to 4 min each) cause most timeouts: 10 of 30 base tasks had one, and 9 of those 10 failed. Every Team B variant that added steps (analyzer-plan 5/30, diff-critic 6/30, patch-hygiene 4/30) scored below base 7/30 because the extra turns came out of the same 4.5 min. `thinking_budget: 4096` did not stop turns above 4,096 tokens, so the hard cap is `max_output_tokens`. 3072 caps a single turn at about 100 s, and it also frees context room (base hit ContextWindowExceededError on fastapi_14186 and rich_3930 with 16384 reserved for output).

**Risk:** a capped turn can end mid-thought with no tool call; the harness already nudges the model to continue in that case.

**Decision rule:** submit to Kaggle only if dev >= 7/30 with fewer timeouts than base (15).

## Results
Dev (30 tasks, run 2026-11-25, kernel g5b-eval-team-b-variants-combined-v1-dev): **5/30**, base 7/30.

| | base | combined-v1 |
|---|---|---|
| Resolved | 7 | 5 |
| Timed out (4.5 min) | 15 | 16 |
| Empty patch | 5 | 3 |
| ContextWindowExceededError | 2 | 0 |
| Turns >= 2,000 tokens | 12 | 1 |
| Longest single turn (tokens) | 4,166 | 2,632 |
| Median first edit (min) | 1.1 | 1.05 |

Passes are a subset of base (fastapi_14077, 14301, 14492, rich_3718, 3905); lost rich_3063 and rich_3278.

The caps did what they were meant to: long turns almost disappeared, context crashes went to 0 and fewer tasks ended without an edit. Timeouts did not drop, so the time freed from long turns went into more short turns (761 agent turns vs 700) rather than into finishing tasks. Long single thoughts were a symptom, not the main cause of timeouts. A 2-task gap on 30 tasks is within run-to-run noise, so this is "no improvement", not proof that the caps hurt.

**Decision:** below the submit bar (>= 7/30); not submitted as of 2026-11-25.
