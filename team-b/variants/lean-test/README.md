**What changed:** Derived from lean-agent at e39e961. Select an existing test by the behavior its assertion checks.
**Why:** A passing test of an unrelated behavior in the same module can give false confidence. Prefer a matching test node within the existing targeted test step.
**Source:** Team B lean-agent and targeted verification design, informed by [4] from the Team B guide.
