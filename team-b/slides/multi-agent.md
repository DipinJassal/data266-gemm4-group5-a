# Slide — Multi-agent (Parth Patel)

**Team B · DATA 266 · Gemma 4 Developer Agent**

## Title
Multi-agent localization and patch review on a fixed budget base

## One-sentence claim
We test two **independent**, one-change interventions on `team-b/variants/base`: require the existing analyzer to plan before edits (V1), and add a single post-edit critic round (V2)—without changing model, adapters, sampling, or the 4.5 min / 50-call budget.

## Design (diagram bullets)
- **Base:** root coder + optional `code_analyzer_agent` (`agent_tool`)
- **V1 `analyzer-plan`:** prompt-only analyzer-first + ≤15-line plan (no new agent)
- **V2 `diff-critic`:** new `diff_critic_agent` reviews real `git diff` once → ≤1 revision → submit

## What we measure (not yet run)
Smoke → (optional train tune) → one `dev` → Team B Kaggle
Track: call order, OK vs problems, revisions, empty patches, time, resolved %

## Status
Source + draft PRs ready · adapters / smoke / dev / Kaggle **pending** · no fabricated scores

## Sources
[3] SWE-Protégé · [6] Category-aware experts · [11] Agentic issue-resolution survey
