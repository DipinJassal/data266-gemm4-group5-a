# Slide — Multi-agent (Parth Patel)

**Team B · DATA 266 · Gemma 4 Developer Agent**

## Title
Multi-agent localization and patch review on a fixed budget base

## One-sentence claim
We test two **independent**, one-change interventions on `team-b/variants/base`: require the existing analyzer to plan before edits (V1), and add a single post-edit critic round (V2)—without changing model, adapters, sampling, or the 4.5 min / 50-call budget.

## Design
- **Base:** root coder + optional `code_analyzer_agent` (`agent_tool`)
- **V1 `analyzer-plan` (`63a3eb2`):** prompt-only analyzer-first + ≤15-line plan
- **V2 `diff-critic` (`2cd4327`):** new `diff_critic_agent` reviews real `git diff` once → ≤1 revision → submit

## Results (label the split)
| | Diagnostic (2) | Smoke (10) | Dev (30) | Official Kaggle |
|---|---|---|---|---|
| Team B base | — | — | **7/30** (team-lead) | — |
| V1 | 1/2 | **0/10** | **5/30** (team-lead) | not confirmed |
| V2 | 1/2 | **1/10** | **6/30** (verified) | not confirmed |

## Selection
Neither multi-agent variant beat base on **dev** → **not selected** for the combined agent. Dev is not an official competition score.

## Mechanism (smoke) — talk track
- **V1:** analyzer called 8/10; **6** analyzer context-window failures; timeouts dominate
- **V2:** critic called **1/10**; **0** completed feedback loops; the smoke resolve was not critic-caused
- Takeaway: honest negative / below-base result under the fixed budget

## Status
Source PRs #13/#14 · metrics PR #18 · docs PR #16 · official multi-agent submission **not confirmed**

## Sources
[3] SWE-Protégé · [6] Category-aware experts · [11] Agentic issue-resolution survey
