# Report section: LoRA fine-tuning (Bhoomika Lnu)

*Draft for the group report.*

## LoRA fine-tuning

**Goal.** The model is fixed (Gemma 4 31B, served as a 4-bit QAT checkpoint), but Kaggle allows a LoRA adapter per agent.
We tested whether a small adapter trained only on the 99 public training tasks helps the agent produce working patches.
Dev tasks were never used for training.

**Feasibility.** Training the 31B model is only possible on Kaggle's 4x L4 GPUs (24 GB each), and only when the
competition is attached to the notebook, which also turns internet off. We trained QLoRA adapters (rank 16, all seven
linear layers, 122M parameters) on the bf16 checkpoint loaded in 4-bit, then served them on the QAT model. Two
memory problems had to be solved: the output layer over the 262K-token vocabulary does not fit for long sequences, so
the loss is computed in 512-token chunks; and examples are capped at about 10K tokens. A tiny test adapter loaded in the
official harness and every request went through it, so the go/no-go was GO.

**V1: LoRA on reference patches.** We turned each training task's reference patch into an agent run in the harness's
exact format (search, read the file, one edit per hunk, compile check, submit) and checked that every run reproduces the
reference patch. 75 runs were used (13 were too long). Training took 82 minutes and held-out loss fell from 1.16 to 0.40.

| Variant | Smoke (10) | Dev (30) |
|---|---|---|
| Baseline (1 min / 10 calls) | | 2/30 |
| Control: budget fix (4.5 min / 50 calls) | 2/10 | not run |
| V1, adapter at full strength | 1/10 (twice) | |
| **V1, adapter at 1/4 strength** | **2/10** | **5/30 (16.7%)** |
| V2, curated runs | 2/10 | not run |

At full strength the adapter hurt. The templated runs contain no thinking and no mistakes, so the model learned to skip
thinking, read tiny file windows and guess edits, and when an edit failed it repeated it up to 14 times. Scaling the
adapter to a quarter of its strength kept the useful part (well-formed edit calls, fewer empty patches: 4 of 30 versus
20 of 30 for the baseline) without the brittle behaviour. The dev score equals the structured-prompt variant built on
the same control, and the control has no dev score yet, so the gain cannot be credited to the adapter alone.

**V2: LoRA on curated agent runs.** To fix V1's weakness, V2 trains on real successful agent runs, which include the
model's own thinking and its recoveries from failed calls. We ran the agent on 60 training tasks, kept only the resolved
runs, and dropped runs where more than 25% of tool calls failed or the same failing call was repeated three times,
following Han [10], who found the error-retry rate the most useful filter. Long runs were split into pieces that fit in
memory, with older tool output shortened as the harness itself does at serving time. The agent resolved 14 of 60
training tasks; 13 runs passed the filter and became 30 training pieces. Training took 99 minutes and held-out loss
(two smoke-task runs) fell from 0.31 to 0.20. The starting loss is already low because the data is the model's own
output, so V2 sharpens what the model does when it succeeds instead of teaching a new style. On smoke V2 also scored 2/10, solving the same two tasks as V1. It kept thinking (no
V1-style collapse) but made fewer tool calls (14 on average versus 22) and left more patches empty (5 versus 1), so we
did not spend a dev run on it. With only 13 successful runs, V2 is a documented negative result: more and stronger
runs would be needed before this approach can help.

**Takeaways.**
1. LoRA on the 31B model is feasible within Kaggle's free GPUs, but only with chunked loss and length limits.
2. Adapter strength matters as much as the data: the same adapter went from hurting to helping when scaled down.
3. Synthetic "perfect" runs teach format but not reasoning; training data should include thinking and recovery.

## Contribution-table row

| Member | Contribution |
|---|---|
| Bhoomika Lnu | LoRA feasibility check on Kaggle (QLoRA on 31B, memory fixes, adapter format accepted by the harness); V1 LoRA on reference-patch trajectories (data pipeline, training, strength study: full strength 1/10 vs 1/4 strength 2/10 smoke, 5/30 dev); V2 LoRA on curated successful agent runs (error-retry filtering, windowed training; held-out loss 0.31 to 0.20, smoke 2/10, a documented negative result); found and documented a harness race that silently ran stale agent uploads. |

## Slide (one slide)

**Title:** LoRA fine-tuning: can a small adapter teach the agent to patch?

- Feasible on Kaggle 4x L4: QLoRA, rank 16, chunked loss, max ~10K tokens
- V1: 75 reference patches turned into agent runs
  - full strength: 1/10 smoke (stops thinking, repeats failed edits)
  - 1/4 strength: 2/10 smoke, **5/30 dev** (baseline 2/30), empty patches 20 to 4
- V2: real successful runs with thinking, filtered by error-retry rate [10]
  - 13 runs, 30 pieces, held-out loss 0.31 to 0.20; smoke 2/10 (no gain over V1)
- Lesson: adapter strength and realistic data matter more than more data
