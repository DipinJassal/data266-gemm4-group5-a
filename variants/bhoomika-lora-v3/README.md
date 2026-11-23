**What changed:** `adapters/main_lora` is Bhoomika's LoRA V3 (r16, all linear layers, trained at alpha 32 and served at alpha 8 like V1/V2) on 21 resolved train-split agent runs (57 pieces; branch `bhoomika/lora-v3`), trained on Dipin's quota Nov 23 (held-out loss 0.309 → 0.194, weights in the private dataset `dipinjassal/g5a-lora-v3-adapter`); everything else is `bhoomika-lora-runs-v2`, i.e. `dipin-step-budget-v1`.
**Why:** same targets as V2 (empty/invalid diffs, malformed edits, `docs/error_analysis.md`) with 21 instead of 13 curated runs.
**Source:** [10] Han, trajectory curation (error-retry filter, held-out loss check), [13] LoRA, [5] Open-SWE-Traces

**Dev (Nov 23, git `afadf9f`): 4/30.** Solved `rich_3278` (new) but lost `fastapi_14301` and `rich_3718`; 4 empty, 22 fail.
