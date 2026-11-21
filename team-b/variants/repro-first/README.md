**What changed:** Added one reproduce-first verification policy through a registered skill and root-prompt invocation: observe an issue-related failure, fix source, rerun the same check, and remove the temporary script.
**Why:** Targets wrong-fix failures and weak local verification while bounding reproduction retries and preventing scratch files from entering the submitted patch.
**Source:** Team B plan references [3] SWE-Protégé and [12] SWE-bench; implemented as the planned reproduce-first skill.
