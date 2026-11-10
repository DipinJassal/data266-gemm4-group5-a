# Local evaluation harness (Dipin, due Nov 12)

Will accept a variant folder and a split (`smoke` or `dev`) and save per-task pass/fail, runtime and run logs.

## Splits (to be filled)

- `splits/smoke.txt` — 10 tasks for quick checks
- `splits/dev.txt` — 30 tasks for scoring, covering all 4 public repos. **Never train or tune on these.**
- `splits/train.txt` — the other 99 public tasks (LoRA training data)

One task ID per line.
