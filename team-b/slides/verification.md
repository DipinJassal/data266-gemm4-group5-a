# Testing and verification

Naveen | Team B | Draft for one presentation slide

**Question:** Can explicit verification improve patches within a 270-second agent budget?

- **Reproduce first:** observe failure, edit source, rerun. R2 requests inline checks and one execution before/after.
- **Regression check:** compare related existing tests before/after editing. Local design only; Poushali coordination and evaluation pending.
- **Control:** independent base copies; unchanged model, sampling and budgets.

| Two-task pilot | Resolved | Min/task | Empty | Scratch-only |
|---|---:|---:|---:|---:|
| Initial | 1/2 | 4.085 | 0 | 1 |
| R2 | 1/2 | 4.565 | 1 | 0 |

**Takeaway:** R2 removed scratch scripts but showed no resolution gain. Its solved task first edited at **217.6/270 seconds**; the failed task never edited. Verification must leave time for a source fix.

Speaker note: Four executions of the same two unique tasks, with one timeout per pilot. No matched base pilot; no general performance claim. Full smoke/dev and official scores remain pending. The historical one-minute baseline is not the control for these 4.5-minute variants. Ashmitha now reports base dev 7/30; those raw artifacts have not been independently checked here.

Sources: [verification section](../report/sections/verification.md) and [error analysis](../docs/error_analysis_b.md).
