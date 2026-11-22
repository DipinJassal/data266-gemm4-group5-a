# Combined agent v2 (Dipin, Nov 23)

Team A (group 5a) changes only; nothing from `team-b/`. Base: `variants/dipin-output-trimming-v1`
(the shortest prompt that scored 5/30 and reached a source edit in the most tasks, 25/30).

| Part | Owner | From |
|---|---|---|
| Per-task budget 4.5 min / 50 calls | Dipin | `variants/dipin-step-budget-v1` |
| Baseline workflow prompt + keep-tool-output-small rules | Dipin | `variants/dipin-output-trimming-v1` |
| **New:** `max_output_tokens` 16384 → 8192 (main agent and sub-agent) | Dipin | config fix found in combined v1 |
| **New:** one pre-submit line: `git status --short` + import each changed module, fix import errors, `rm` scratch files | Dipin | patch-hygiene check |

**Why 8192:** with 16384, vLLM rejects any request once the input passes 16,384 tokens, so every variant had only half of
the 32K window; this caused every context-window crash logged so far. 8192 still covers the 4,096-token thinking budget
plus tool-call arguments, and leaves ~24K tokens for input.

**Left out on purpose:** Khushi's structured loop and Sarvesh's single retry. Each tied or matched alone, but stacked with
extra rules in v1 they made the agent investigate longer and edit later (see below). Bhoomika's LoRA: no gain over the prompts.

## History

- **v1 (Nov 22, tag `combined-v1-negative`): dev 4/30, negative, not submitted.** Structured prompt + output trimming +
  single retry + five new rules, 4.0 min. 13 empty patches vs 5; only 17/30 tasks reached an edit. Details: `docs/combined_v1_analysis.md`.

**Sources:** [9] Codebase-Memory, [7] RepoAtlas, [3] SWE-Protégé, [12] SWE-bench.
