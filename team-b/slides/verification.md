# Testing and verification

Naveen | Team B | Draft for one presentation slide

**Question:** Can explicit verification improve patches within the same 4.5-minute budget?

- **V1 — Reproduce first:** load the skill → observe an issue-related failure → edit source → rerun the check. Initial policy used scratch scripts; R2 requests inline checks and one execution before/after.
- **V2 — Regression check:** select related existing tests → record pre-edit outcomes → edit source → rerun → correct a confirmed new regression once. No test edits or full-suite runs.
- **Control:** each variant independently starts from the budget-fixed Team B base; model, sampling and budgets stay unchanged.
- **Evidence so far:** both local validators pass. Initial and R2 pilots each resolved 1/2 of the same two tasks. Mean task time rose from 4.085 to 4.565 min. R2 removed scratch scripts from final patches, but the failed task still timed out with no source fix and attempt limits were ignored. No improvement demonstrated; full smoke/dev and official scores remain pending. V2 coordination with Poushali is pending.
- **Trade-off to measure:** stronger checks may catch mistakes but leave less time for source edits. A passing local check is not proof of a passing hidden test.

Speaker note: Team A's historical dev baseline had 23/30 tasks with no source change and five failed source patches whose wrong-fix/regression causes could not be separated. That one-minute baseline is context, not the matched control for these 4.5-minute variants. Do not claim an improvement until the runs are complete.

Sources: [verification section](../report/sections/verification.md) and [error analysis](../docs/error_analysis_b.md).
