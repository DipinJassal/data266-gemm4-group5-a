# DATA 266 Group 5 — Gemma 4 Developer Agent (team of 5)

Autonomous software-engineering agent for the Kaggle **Gemma 4 Developer Agent** competition.
Given a Python repository and a bug report, the agent finds the problem, edits the code and submits a patch.
We start from the sample agent and improve it **one change at a time**.

**Read [CLAUDE.md](CLAUDE.md) first** — it has the rules, roles, submission calendar and references.

## Layout

| Path | What | Owner |
|---|---|---|
| `baseline/` | Unmodified sample agent. **Never edit.** | Sarvesh |
| `variants/<owner>-<name>-v<n>/` | One folder per variant (copy of baseline + one change) | Each member |
| `harness/` | Local evaluation harness and task splits | Dipin |
| `docs/` | Run guide, baseline profile, error analysis | Sarvesh, Khushi |
| `lora/` | LoRA training scripts, data prep, adapter configs | Bhoomika |
| `combined/` | Combined agent (best variants merged) | Dipin |

## Making a variant

```bash
cp -r baseline variants/<owner>-<short-name>-v1
cp variants/_template/README.md variants/<owner>-<short-name>-v1/README.md
# make ONE change, fill in the 3-line README, open a PR, request your reviewer
```

Review rotation: Dipin → Sarvesh → Khushi → Poushali → Bhoomika → Dipin. Nobody approves their own variant.
