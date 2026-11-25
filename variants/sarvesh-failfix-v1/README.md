**What changed:** `prompts/system.md` only — replace the soft “test then submit” step with a mandatory **fail→fix** loop: after the first successful source edit, run one targeted pytest immediately; on a failure caused by your change, make exactly one alternate fix (overwrite, not stack), re-check once, then submit; skip the retry if under ~90s remain or the failure is env/untouched-package. Everything else is copied unchanged from `dipin-base-v2` (7 min / 50 calls / 80 turns, output-trimming, `max_output_tokens` 8192, edit-by-~15, `git grep`, patch hygiene, one-word exit).

**Why:** skills pack and base-v2 both score **6/30 on the same six tasks**. The largest addressable gap is wrong/incomplete patches after an edit. Prior `sarvesh-best-of-n-v2` (prompt retry on the 4.5 min control) rarely reached a failed targeted check. Fail→fix sits on the 7 min base so pytest-after-edit and one retry can finish.

**Source:** [4] SWE-Master / test-time scaling (multiple attempts), adapted as a single declarative retry; base = `dipin-base-v2`.

**Not changed:** `eval_config.yaml`, `configs/sampling.yaml`, `agent.yaml`, adapters, analyzer, tools.
