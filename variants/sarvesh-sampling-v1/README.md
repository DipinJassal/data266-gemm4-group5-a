**What changed:** `configs/sampling.yaml` only — thinking off (`thinking_budget: 0`, `include_thoughts: false`); temp/top_p unchanged. Built on `dipin-step-budget-v1` budget (4.5 min / 50 calls), not the 1-min baseline.
**Why:** baseline profile: ~96% of wall time was model wait; a 4096-token thinking budget at ~29 tok/s can burn the whole task before edits (targets timeout / empty-diff).
**Source:** [4] SWE-Master (test-time scaling / decode settings); profile in `docs/baseline_profile.md`
