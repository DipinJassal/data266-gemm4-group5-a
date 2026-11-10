# Baseline — unmodified sample agent

Exact copy of `sample_submission/` from the Kaggle competition data (files dated Oct 13, 2026), added Nov 9.
Every file except this README is byte-identical to Kaggle's (`diff -r data/sample_submission baseline`).
The adapters in `adapters/` are Kaggle's dummy placeholders (rank 4, layer 0 only).

Note: `eval_config.yaml` limits each task to **1 minute and 10 tool calls**.

**Never edit this folder.** Copy it into `variants/` to make a change.
