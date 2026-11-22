# CLAUDE.md — DATA 266 Group 5, Gemma 4 Developer Agent (Kaggle team of 5)

This file tells Claude (and every teammate) what the project is, how the repo is organized, and who owns what.
Read it before making changes. Keep it up to date as setup items are finished.

## Project in one paragraph

We are building an autonomous software-engineering agent for the Kaggle **Gemma 4 Developer Agent** competition.
Given a Python repository and a bug report, the agent finds the problem, edits the code and submits a patch.
Kaggle runs hidden tests on each patch; the score is the percentage of issues resolved. We start from the
**sample agent** and improve it **one change at a time**, so the final report can show which changes helped
and which failed. Our group of 9 is split into two Kaggle teams (5 + 4). **This repo is the team of 5.** The
report and presentation are shared with the other team.

## Competition rules

Source: Kaggle's official `HARNESS_README.md` in the competition data (download with the Kaggle CLI into `data/`).
Items marked *(Rules tab)* still need checking on the Kaggle Rules page.

- **One base model per submission**, shared by every agent and sub-agent. Kaggle allows 4 quantized models
  (`gemma-4-31b-it-qat-w4a16-ct`, `-12b-`, `-e4b-`, `-e2b-`); **our team uses `gemma-4-31b-it-qat-w4a16-ct`** (proposal).
  LoRA adapters are optional, may differ per sub-agent, `.safetensors` only, rank ≤ 128.
- A submission is a **`submission.zip` with `agent.yaml` at the root**, declarative YAML only (no Python entry point).
  Tools: only the 9 harness tools (`run_command`, `submit_patch`, `get_status`, `read_file`, `edit_file`, `write_file`,
  `get_code_neighbors`, `search_similar_code`, `get_code_subgraph`) or `agent_tool` sub-agents; skills are folders with `SKILL.md`.
  Allowed file types: `.yaml .yml .md .txt .py .json .safetensors`. No symlinks, no paths outside the root, total < 3 GiB.
- **12-hour runtime** for ~120 hidden tasks, including sandbox setup, excluding patch validation → about **6 minutes per task**.
  The per-task agent budget is set in the submission's `eval_config.yaml` (`max_time_minutes`, `max_tool_calls`, `max_turns`).
- Context window is **32,768 tokens** (`max_output_tokens` and `thinking_budget` ≤ 32,768). Sandbox: offline, 4 GiB RAM, 2 vCPUs.
- A task counts as resolved only if the hidden tests pass. Changes to test files and test config are stripped before scoring.
- **1 submission per team per day** *(Rules tab)*. Kaggle's day resets at 4:00 pm Pacific (00:00 UTC). Up to 2 final submissions.
- Hidden tasks come from **private repos**, not the 4 public ones (FastAPI, Rich, Requests, HTTPX).
- Winners must release code under Apache 2.0 *(Rules tab)*. This repo is public.

## Team

| Member | Role | Area (2 variants each) | Reviewed by |
|---|---|---|---|
| **Dipin Jassal** | Captain; starts the project (Kaggle team, repo, evaluation harness) | Context & time budget; combined agent | Bhoomika |
| **Sarvesh Reshimwale** | Starts the project (sample agent running, run guide, baseline, time profile) | Sampling & multiple attempts | Dipin |
| **Khushi Donda** | Team experiment log; baseline error analysis | Prompts | Sarvesh |
| **Poushali Deb Purkayastha** | Confirms allowed tools and skill formats | Skills & tools | Khushi |
| **Bhoomika Lnu** | LoRA feasibility check (highest risk) | LoRA fine-tuning | Poushali |

Review is a rotation: Dipin → Sarvesh → Khushi → Poushali → Bhoomika → Dipin. Nobody approves their own variant.

## Status (last updated Nov 21, 2026)

**Scoreboard (local harness; smoke = 10 train tasks, dev = 30 held-out tasks)**

| Variant | Owner | Change (vs control) | Smoke | Dev | Kaggle |
|---|---|---|---|---|---|
| `baseline` | — | unmodified sample (1 min / 10 calls) | — | **2/30** | not submitted |
| `dipin-step-budget-v1` (control) | Dipin | 4.5 min / 50 calls | 2/10, 1/10 | **not run** | not submitted |
| `khushi-structured-prompt-v1` | Khushi | structured-loop prompt | 1/10 | **5/30** | not submitted |
| `khushi-anti-looping-v2` | Khushi | time-budget prompt | 2/10, 1/10 | — (negative, closed) | — |
| `sarvesh-sampling-v1` | Sarvesh | thinking off | 2/10 | — | not submitted |
| `bhoomika-lora-patches-v1` | Bhoomika | LoRA on reference patches (alpha 8) | 2/10 | **5/30** | **submitted Nov 22** (ref 58709756, pending) |
| `bhoomika-lora-runs-v2` | Bhoomika | LoRA on curated agent runs (alpha 8) | 2/10, 1/10 (18-run retrain) | — (neutral, no dev) | merged #19 |
| `sarvesh-best-of-n-v2` | Sarvesh | prompt-only single retry | 2/10 | — | merged #21 |
| PR #22 skills pack V1 | Poushali | fix-and-verify skill | 1/10 (negative) | — | open PR (Khushi reviews) |
| PR #23 test-runner V2 | Poushali | test-runner `agent_tool` | negative | — | open PR (Khushi reviews) |
| `dipin-output-trimming-v1` | Dipin | "keep tool output small" prompt section | skipped (straight to dev) | **5/30** (1 context crash vs 2 for Khushi's V1; avg 3.9 min) | — |
| Combined agent v1 | Dipin | Team A merge: structured prompt + output trimming + single retry + import/scratch-file checks, 4.0 min | — | **running (Nov 22)** | — |

**All three 5/30 variants (structured prompt, output trimming, and per-repo counts for LoRA V1) solve the same tasks:** fastapi_14077, fastapi_14301, fastapi_14492, rich_3718, rich_3905. That points to the shared 4.5 min / 50-call budget doing the work, so the V2 control's own dev/Kaggle score is the most important missing number.
Takeaways: every variant lands at 1–2/10 on smoke, and the control alone scored 2/10 and 1/10, so **smoke is too noisy to rank variants**; only dev tells them apart.
7/30 dev tasks can't pass in our harness (missing test packages, `docs/scoring_environment_comparison.md`), so 23/30 is the local ceiling.
**First Kaggle submission: Nov 22, `bhoomika-lora-patches-v1`** (ref 58709756). Dipin makes all submissions (1 per team per day).
**How to submit (code competition):** uploading a zip with `kaggle competitions submit -f` fails with 400. The submission must be a notebook's
`/kaggle/working/submission.zip` output: push a CPU notebook (internet off, competition + `dipinjassal/g5a-agents` attached) that copies the variant
folder and zips it (example: kernel `dipinjassal/g5a-submit-bhoomika-lora-patches-v1`), then
`kaggle competitions submit gemma-4-developer-agent -k <user>/<kernel> -f submission.zip -v <version> -m "..."`.

**Done**
- Repo created and public: https://github.com/DipinJassal/data266-gemm4-group5-a. All 4 teammates invited with write access (Sarvesh0827, Poushali0202, khushidonda, bhoomikaa); each must accept the invite.
- Kaggle CLI installed on Dipin's Mac; competition data downloaded into `data/` (git-ignored; snapshots, 21.5 GB, not yet downloaded).
- Rules section above updated from Kaggle's official `HARNESS_README.md`.
- `harness/make_splits.py` → `harness/splits/`: **dev 30** (fastapi 15, rich 11, requests 3, httpx 1), **train 99**,
  **smoke 10** (a subset of train, so tuning on smoke never touches dev). Deterministic (seed 266).
- `harness/validate.py`: offline pre-check of a variant folder (rule 6 items) and `--zip` to build `submission.zip`.
- `harness/run_kaggle.py` + `kaggle_runner.py` + `summarize.py`: score a variant on a split in a Kaggle GPU kernel
  from your laptop, then get per-task pass/fail, time, tool calls and a baseline comparison.
  **Confirmed on a real Kaggle GPU (Nov 9, 2 smoke tasks):** `NvidiaL4` = 4 GPUs (tp=4); package install ~1.5 min, vLLM start ~7.5 min,
  plus queueing before the kernel starts (~30 min that time). Baseline: **0/2, both empty patches, both cut off at the 1-minute limit**
  after 8–9 tool calls (~7 s per tool call). In both tasks the agent had already found the right file (`fastapi/dependencies/utils.py`) but hadn't edited it yet.
- `baseline/` filled with Kaggle's unmodified `sample_submission/` (byte-identical; Dipin, Nov 9, so the harness could be tested).
- Draft **V2** `variants/dipin-step-budget-v1/`: only `eval_config.yaml` changed (4.5 min / 50 tool calls instead of 1 min / 10).
  Validated offline; not yet scored. The numbers get tuned after the first smoke timings.

- **LoRA go/no-go: GO** (Bhoomika, PR #3, merged Nov 13). Tiny QLoRA adapter trained on bf16 31B (L4×4) loads on the served QAT model in the harness, no errors (2-task load test: 1/2, not a score). V1 training ≈ 2–3 h of quota per run. Setup notes in `lora/README.md`.
- **Bhoomika V1 `bhoomika-lora-patches-v1`** (PR #12, merged Nov 20): V2 + LoRA trained on 75 train-split reference-patch trajectories, served at alpha 8. Smoke 2/10 (same as control), **dev 5/30 = 16.7%**, avg 3.4 min. Alpha 32 got 1/10 on smoke twice (overfit, repeats failing edits). Weights are in the private Kaggle dataset `bhoomikalnu/g5a-lora-v1-adapter` (not in git).

**Next for Dipin**
- [x] Create the Kaggle team, invite all 4, agree the team name with the other team. *(Team in place, confirmed Nov 21.)*
- [ ] Check the items marked *(Rules tab)* above on the Kaggle Rules page and post the rules to the team.
- [x] First real harness run (2 smoke tasks). Three launcher bugs were found and fixed along the way (Python literal, push hang, pinned Python 3.12 image).
- [ ] Announce the harness to the team (`harness/README.md`).
- [x] **Baseline on dev (Nov 10): 2/30 = 6.7%**. 20 empty patches, 8 wrong patches; avg 1.1 min per task (1-minute limit).
  Per repo: fastapi 1/15, rich 1/11, requests 0/3, httpx 0/1. Log this as the team's dev baseline.
  *Verified by Khushi (Nov 12) from the run ZIP: every figure matches; 28/30 tasks ended on the 1-minute timeout. Details: `docs/error_analysis.md`.*
- [x] **V2 `dipin-step-budget-v1` on smoke (Nov 10): 2/10**, no crashes, avg 4.2 min per task (max 4.8, under the 6 min target).
  3 empty patches, 5 wrong. The 2 smoke tasks the baseline failed in the harness test now pass. Smoke is part of train, so this isn't a dev score.
- [ ] Run V2 on dev (~2.5 h of GPU time) for the real comparison against 2/30 **(now urgent: Bhoomika's and Khushi's V1 both got 5/30 on top of V2, and neither gain can be credited until V2 has a dev score)**, then pick its `Source:` reference and submit on a spare slot.
- [x] Fix the `run_kaggle.py` race Bhoomika found. *(Branch `dipin/output-trimming-v1`, not yet on main: each upload gets an `upload_id`, and the kernel stops with "STALE UPLOAD" if the mounted dataset doesn't match.)*
- [x] Get access to `bhoomikalnu/g5a-lora-v1-adapter`. *(Shared Nov 21. Downloaded and checked: config identical to the repo's, 820 bf16 tensors, rank 16, all 60 layers, language model only.
  Copied into `variants/bhoomika-lora-patches-v1/adapters/` (git-ignored) and built `harness/runs/bhoomika-lora-patches-v1-submission.zip` (183 MiB, validates).)*
- [ ] **Daily Kaggle submissions** (Dipin only). Nov 22: `bhoomika-lora-patches-v1` ✅. Next: Nov 23 `dipin-output-trimming-v1` if it beats 5/30 on dev, else `khushi-structured-prompt-v1`;
  Nov 24 `dipin-step-budget-v1` (budget-only reference); then baseline, the other 5/30 variant, combined agent. Pick the final 2 by Dec 2.
- [x] Review PRs. *(Nov 21: #19 and #21 approved and merged; #22 and #23 commented, waiting on Khushi's questions; they'll need a rebase on `docs/experiment_log.md`.)*
- [ ] Combined agent (Nov 23). **v1 built Nov 22** on branch `dipin/combined-v1` (stacked on PR #24), Team A work only (nothing from `team-b/`): Khushi's structured loop + Dipin's output-trimming rules + Sarvesh's single retry + new checks aimed at the 25 unsolved dev tasks (import check of changed modules, fix imports on rename, delete scratch files, exact new-parameter names). Budget cut to **4.0 min** / 50 calls so ~120 Kaggle tasks stay well under the 12-hour limit (worst case ~9 h). LoRA left out (no gain over prompts; v2 candidate). Dev run on Kaggle started Nov 22 (`g5a-eval-combined-dev`). Details: `combined/README.md`. Next: if it beats 5/30, submit it on Nov 23; otherwise use that slot for the V2 control.
- [ ] V1 output trimming: `dipin-output-trimming-v1` on branch `dipin/output-trimming-v1` scored **5/30 on dev** (Nov 22; same 5 tasks as Khushi's V1). Open a PR (reviewer: Bhoomika); the branch also carries the harness upload_id fix (confirmed working in this run).
- [x] Nov 12: send Khushi the baseline dev run ZIP (prepared: `harness/runs/baseline-dev-20261110.zip`, local and git-ignored): results, patches,
  traces, readable logs. That run did **not** save Phase 2 test output; `kaggle_runner.py` now saves each task's full result to `task_details/`.
  *(Received by Khushi Nov 12; analysed in `docs/error_analysis.md`. The ZIP itself stays out of git.)*
- [x] Nov 13: fixed `task_details/` (reported by Khushi): `model_dump(mode="json")` failed on the `SessionTrace` field, so nothing was saved. Now saved field by field; trace fields are skipped (already in `swegemma/traces/`). Tested on a mock result; first real run will confirm the Phase 2 output is in there.
  *(Confirmed by Khushi, Nov 14: in two real 10-task smoke runs every task saved `task_details/`, and every non-empty patch (4/4 and 8/8) has its Phase 2 `test_output`. Empty patches skip Phase 2 by design.)*
- [ ] Decide how run results reach the team: ZIPs by hand (now), or commit small run summaries to the repo.

- [ ] Pick the paper reference for V2's README (`Source:` line), then smoke → dev → log it.
- [ ] Ask the team: should V1 variants be built on top of the budget-fixed V2 instead of the 1-minute baseline? (See findings.)

**Next for others**
- [ ] **Sarvesh:** `baseline/` is already filled (unmodified sample). Run guide + baseline profile written (`docs/run_guide.md`, `docs/baseline_profile.md`). Still open: official team Kaggle baseline submission (or confirm Dipin's Nov 10 harness 2/30 is the recorded team baseline).
- [ ] **Everyone:** install the Kaggle CLI, accept the competition rules, save your API token (see `harness/README.md`), so you can run the harness on your own GPU quota.

- **Khushi (Nov 13):** V1 structured-loop prompt ran on Kaggle (4× L4) on her own quota: **1/2 smoke tasks** (quick check, not a score). Full smoke run next, now that `task_details/` is fixed.
- **Khushi (Nov 14):** V1 10-task smoke **1/10**; the matched control (`dipin-step-budget-v1`, unchanged, same tree `82853e5e`, same settings) also scored **1/10**,
  on the same task. Exploratory (n=10, one run each). Details: `docs/v1_smoke_analysis.md`.
- **Khushi (Nov 14):** V1 on dev (RUN-007, one full run, 4.5 min / 50 calls): **5/30 = 16.7%** (fastapi 3/15, rich 2/11, requests 0/3, httpx 0/1).
  Not a controlled gain over the baseline's 2/30, which ran at 1 min / 10 calls; the control has no dev score yet. Details: `docs/v1_dev_analysis.md`.
- **Khushi (Nov 15):** V2 time-budget prompt (`khushi-anti-looping-v2`), two smoke iterations against the control's RUN-006 (1/10): RUN-008 **2/10**, RUN-009 **1/10**.
  In neither did the agent call `get_status()` more than once (0/10 tasks), so the time rules never fired. V2 is closed as a documented negative result:
  no dev run, not proposed for submission. Details: `docs/v2_time_awareness_analysis.md`; log rows pending PR #5: `docs/v2_experiment_log_entries.md`.

**Findings the team needs to know**
- **Everyone:** the official local evaluator is `swegemma` (not on PyPI; installed from the Kaggle dataset
  `metric/gemma-4-developer-agent-wheelhouse` inside a Kaggle notebook). Running the agent needs an L4×4 GPU, so scored runs happen on Kaggle, not laptops.
  The official "Getting Started" notebook (`ryanholbrook/getting-started-gemma-4-developer-agent`) is the reference.
- **Sarvesh:** the sample `eval_config.yaml` caps each task at **1 minute and 10 tool calls**, so the unmodified baseline will likely score very low.
  Submit it unchanged (it's the baseline), but note this in `docs/baseline_profile.md`.
- **Poushali:** the allowed tools and skill format are listed in the Rules section above (from `data/HARNESS_README.md` §2 and §6), which covers most of the Nov 11 setup task.
- **Bhoomika:** the sample adapters are dummies (rank 4, layer 0 only, `q_proj`/`o_proj`). Limits: `.safetensors`, rank ≤ 128, whole zip < 3 GiB (§3.4 of the harness doc).
- **Dipin (V2):** the per-task budget lives in `eval_config.yaml`; 12 h / ~120 tasks leaves about 5 minutes of agent time after setup.
- **Khushi:** in the first real run the agent re-read the same file range three times in a row and once invented an argument name
  (`start_line"`). That's early evidence for the anti-looping prompt. Traces are in `harness/runs/.../swegemma/traces/` after a run.
  In the baseline dev run, 10/30 tasks produced a patch; at least one patch includes a stray scratch file (`repro.py`), which matters for patch hygiene in the combined agent.
- **Everyone (baseline error analysis, Nov 12; full detail in `docs/error_analysis.md`):**
  23/30 final patches change no source file: 20 empty, plus 3 that contain only a scratch script. In 18 of those 23 the agent had already opened a file
  from the reference patch; only 7/30 ever made a successful source edit. Of 1,960 s total wall-clock, about 96% was spent waiting for the model
  (between calls, or after the last call until the cut-off) and 0.4% on tool execution; effective throughput was about 29 tokens/s.
  Malformed tool-call arguments appear in 8/30 tasks, and in one (`fastapi_14258`) they made every edit fail. No task ran the repo's own tests.
  6 of the 8 failing patches include scratch files. "Wrong fix" and "broke other tests" can't be separated, because Phase 2 output wasn't saved.
  These are dev-set patterns: confirm them on smoke/train runs before designing variants around them (rule 3).
- **Everyone (`requests` tasks, Nov 14; detail in `docs/httpbin_investigation.md`):** the test environment lacks `pytest-httpbin`, so every
  `httpbin` test in the requests repo's `tests/test_requests.py` errors (`requests_7505`: 197 errors in our Kaggle run). In a local reproduction of the sandbox,
  the official reference patch gets the same 197 errors, so the task can't be resolved there. 8 of 13 public `requests` tasks target that file
  (inferred; only `requests_7505` tested), including smoke `requests_7505` and **dev `requests_7433`**. Report results with and without them.
  Not verified against Kaggle's official Stage 2 scorer.
  *Update (Nov 15): seen directly on dev `requests_7433` in the V1 dev run (195 `httpbin` errors).*
- **Everyone (missing fastapi test dependencies, Nov 15; detail in `docs/v1_dev_analysis.md`):** in our evaluator, 6 of 15 dev fastapi tasks
  (`fastapi_12942`, `13207`, `13713`, `14246`, `14303`, `14356`) fail test collection with `No module named 'dirty_equals'` or `'inline_snapshot'`.
  Neither package is among the competition wheels, and test files are reset before scoring, so these tasks can't pass for any variant (the baseline included).
  Together with `requests_7433`, **7/30 dev tasks** are blocked this way (smoke: control's `fastapi_14962`). Cause: our runner, like Kaggle's official
  Getting Started notebook, uses swegemma's subprocess sandbox, where test-dependency installation is skipped entirely. The official Stage 2 scorer uses
  a Docker path with what looks like a private ~1.7 GB wheels cache, so it very likely has these packages (not verified).
  Report each full local 30-task dev result, with a 23-task sensitivity analysis alongside (never as a replacement). These are not Kaggle's official scores. Details: `docs/scoring_environment_comparison.md`.
- **Everyone (adapter weights):** `.gitignore` excludes `*.safetensors`, but `harness/validate.py` requires `adapters/*/adapter_model.safetensors`,
  so validation (and therefore `run_kaggle.py`) fails on every fresh clone, `baseline/` included. Workaround: download Kaggle's
  `sample_submission/adapters/*/adapter_model.safetensors` into your local folder. Fixed locally for `khushi-structured-prompt-v1` only;
  a repo-wide fix (commit the two small dummy files or add a `.gitignore` exception) is Dipin's call.
- **Everyone (proposal, needs a team decision):** because the baseline is capped at 1 minute / 10 tool calls, a prompt or sampling
  change built on it will barely show an effect. Proposal: score V2 (budget fix) first, then build V1 variants on top of it.
  "One change" is then measured against V2, and the report states this.
  *Status (Nov 12): Khushi's V1 follows this proposal (see her section). It is recorded as **proposed, pending Dipin's formal confirmation**;
  rule 1 below is unchanged until the team confirms.*
- **Submissions are declarative only** (YAML + prompts + skills), with no Python hooks. Output caps (5,000 chars per command,
  150 lines per `read_file`) and the summarizing of older turns are fixed by Kaggle's harness, so a variant can't change them.
  That affects Dipin's V1 (output trimming → do it through prompt rules or an `agent_tool` sub-agent that reads files)
  and the patch-hygiene check in the combined agent (→ a prompt checklist).

## Repo layout

```
data/                       Competition data from Kaggle (git-ignored; see "How to run")
baseline/                   Unmodified sample agent. Never edit.
variants/<owner>-<name>-v1/ One folder per variant: agent.yaml + README.md (+ skills/tools/adapters it needs)
harness/                    Local evaluation harness and task splits (Dipin)
  make_splits.py            Rebuilds the splits from data/tasks.jsonl
  validate.py               Offline variant check + submission.zip builder
  run_kaggle.py             Laptop: launch a scored run on a Kaggle GPU, fetch + summarize results
  kaggle_runner.py          Runs inside the Kaggle kernel (vLLM + official swegemma Evaluator)
  summarize.py              Per-task table, score, time per task, baseline comparison
  runs/                     Downloaded run results (git-ignored)
  splits/smoke.txt          10 tasks for quick checks (subset of train)
  splits/dev.txt            30 tasks for scoring; never train or tune on these
  splits/train.txt          The other 99 public tasks (LoRA training data)
docs/run_guide.md           How to run the agent and build a submission (Sarvesh)
docs/baseline_profile.md    Time/turns per task and longest tool outputs (Sarvesh)
docs/error_analysis.md      Baseline failures labeled by type (Khushi)
lora/                       Training scripts, data prep, adapter configs (Bhoomika)
combined/                   The combined agent (Dipin)
```

Variant folder names: `<owner>-<short-name>-v<n>`, e.g. `khushi-structured-prompt-v1`, `sarvesh-best-of-n-v2`.

Each variant `README.md` has exactly three lines:
1. **What changed** (one change from the baseline)
2. **Why** (which failure type it targets)
3. **Source** (which paper, by reference number below)

## Rules for every change (Claude: enforce these)

1. **One change per variant**, relative to `baseline/`. Only `combined/` mixes changes.
2. **Never edit `baseline/` or another member's variant folder.** Copy the baseline into a new folder instead.
3. **Never train or tune on `harness/splits/dev.txt` tasks.** LoRA trains only on `train.txt`.
4. **Keep changes general.** No hard-coded paths, file names or logic specific to FastAPI, Rich, Requests or HTTPX.
5. **Stay inside the runtime budget.** Average time per task on the smoke set must stay under about 6 minutes.
6. **Before review:** smoke set runs with no crashes → dev-split score logged next to the baseline → `agent.yaml` validates → zip has `agent.yaml` at the root → only allowed tools used.
7. **Log every run** in the team experiment log, including failures. A variant that scores below baseline can still be submitted; documented failures count in the report.
8. **Submit only through the team's Kaggle account**, on your calendar date, after reviewer approval the day before.

## How to run (filled in during setup)

- Get the competition data (once per machine, after accepting the rules on Kaggle and saving your API token in `~/.kaggle/`):
  `kaggle competitions download gemma-4-developer-agent -f tasks.jsonl -p data` (repeat `-f` for `HARNESS_README.md`, `sample_submission/...`).
- Run the sample agent and build a submission: see `docs/run_guide.md` (Sarvesh, Nov 10).
- Check a variant and build its zip (works on any laptop, no GPU):
  `python harness/validate.py variants/<folder> --zip submission.zip`
- Score a variant on a split (Kaggle GPU, your quota): `python harness/run_kaggle.py variants/<folder> smoke` (or `dev`).
  Results go to `harness/runs/`; details in `harness/README.md`. Expect ~10 min of start-up per run, plus Kaggle queue time.

## Individual tasks

### Dipin Jassal — captain, starts the project, Context & time budget

**Setup (starting today):**
- [ ] **Nov 9–10:** Confirm the rules on the Kaggle Rules tab and post them to the team. Create the Kaggle team and invite all 4. Agree the team name (`Group_5_a` or `Group_5_b`) with the other team. *(Rules mostly confirmed from the official harness doc; Rules-tab items and Kaggle team still open.)*
- [x] **Nov 10:** Create this repo with the layout above and the README template. *(Done Nov 9; public on GitHub.)*
- [ ] **Nov 12:** Local harness, with `smoke.txt` (10 tasks), `dev.txt` (30 tasks, covering all 4 repos) and `train.txt` (the other 99). *(Splits ✅, validator ✅, Kaggle runner + summary ✅, confirmed on a real GPU run Nov 9 ✅.)*

**Variants:**
- **V1, Nov 16 — Output trimming:** cap long tool outputs (file reads, test logs) and summarize older turns.
  *Kaggle's harness fixes the caps and the summarizing, so do it either through prompt rules for output (head/grep/line ranges/`pytest -q --tb=short`)
  or through an `agent_tool` sub-agent that reads files and returns a short report. Pick one.*
- **V2, Nov 21 — Step and time budget:** per-task step cap sized to about 6 minutes, with a forced submission of the best diff so far.
  *Drafted as `variants/dipin-step-budget-v1` (eval_config only). The harness already scores unsubmitted diffs, so forced submission needs no change. Proposed to move earlier (spare slot Nov 11/12).*
- **Combined agent, Nov 23:** merge everyone's best variant into one `agent.yaml`, and add a patch-hygiene check (reject empty or non-applying diffs, strip stray debug files).

**Other:** owns the submission calendar and slot swaps; reviews Sarvesh; picks the 2 final submissions by Dec 2; sends Kaggle evidence (team name, members, submission history, scores, best result, screenshots) for the report on Nov 24 and after Dec 2.

**Read:** [12] SWE-bench, [7] RepoAtlas, [9] Codebase-Memory, [3] SWE-Protégé.

### Sarvesh Reshimwale — starts the project, Sampling & multiple attempts

**Setup (starting today):**
- [x] **Nov 9–10:** Get the sample agent running end to end in a Kaggle notebook. Write `docs/run_guide.md` (how to run a few tasks, how to zip and submit).
  *(Nov 13: `docs/run_guide.md` filled — harness path + official notebook + validate/zip + submit steps. End-to-end GPU run was done via Dipin's harness.)*
- [ ] **Nov 10:** Submit the baseline. Share its run logs with Khushi.
  *(Harness baseline scored 2/30 on Nov 10; ZIP shared with Khushi by Dipin Nov 12. Official team-account Kaggle submission still to confirm with Dipin.)*
- [x] **Nov 11–12:** Write `docs/baseline_profile.md`: average time and turns per task, slowest tasks, longest tool outputs.
  *(Nov 13: filled from the Nov 10 `baseline-dev` run numbers verified in Khushi's error analysis. Notes the 1 min / 10 tool-call cap.)*

**Variants:**
- **V1, Nov 14 — Sampling settings:** small sweep of temperature / top-p and thinking mode on vs off on the smoke set; submit the best.
  *Progress (Nov 13–14):* `variants/sarvesh-sampling-v1/` (thinking off on V2 budget). Full smoke **2/10** (ties `dipin-step-budget-v1`); logs in `docs/runs/sarvesh-sampling-v1-smoke-full-20261114T031152Z/`. Harness path fix: `\` → `/` in `run_kaggle.py` / `kaggle_runner.py`. **Next:** Nov 14 team Kaggle submit after Dipin review; optional temp trials / dev later.
- **V2, Nov 19 — Best-of-N attempts:** several attempts, keep the patch that passes the agent's own reproduction test, stop early on a pass. If `agent.yaml` can't express this, use "if your test fails, retry once with a different approach."
  *Progress (Nov 21):* `variants/sarvesh-best-of-n-v2/` (prompt-only single retry on `dipin-step-budget-v1`). Smoke **2/10** (RUN-S02; 4 empty, 4 failed; avg 4.32 min). Logged in experiment workbook. **Next:** Dipin review + rescheduled Kaggle submit slot (Nov 19 missed). Optional later V3: lower `max_output_tokens` (context crash on `fastapi_14609`).
- **V3 (optional):** max output tokens or step-limit tuning.

**Other:** reviews Khushi.

**Read:** [4] SWE-Master (test-time scaling: 61.4% → 70.8% at 8 attempts), [5] Open-SWE-Traces, [3] SWE-Protégé.

### Khushi Donda — Prompts, team experiment log, error analysis

**Setup:**
- [ ] **Nov 10:** Team experiment log (shared sheet) with columns: variant, owner, one-line change, smoke time, dev score, Kaggle score, status, notes.
  *(Nov 12: built as `docs/experiment_log.xlsx` with those columns first; PR #1 approved by Sarvesh and merged Nov 14. The baseline dev run is verified
  against the raw run ZIP; all other runs are marked repo-reported. Still to agree: whether the repo file or a shared sheet is the canonical copy.)*
- [x] **Nov 11–12:** `docs/error_analysis.md`: label every baseline failure as wrong file found, right file but wrong fix, broke other tests, timeout or looping, or empty/invalid diff. Share the counts.
  *(Nov 12: done from the baseline dev ZIP. Primary labels: resolved 2, empty/invalid diff 23, wrong fix or broke other tests 5 (not separable), wrong file 0;
  timeout is recorded as a contributing flag in 28/30.)*

**Variants:**
- **V1, Nov 13 — Structured loop prompt:** reproduce → localize → plan → edit → test → submit, with a short checklist before submitting.
  *Progress (Nov 12):*
  - Implemented as `variants/khushi-structured-prompt-v1/` on local branch `khushi/structured-prompt-v1`, commit `1452729` (not pushed yet).
  - Offline validation passed (`validate.py` OK; zip has `agent.yaml` at root), after downloading the genuine Kaggle sample adapter weights locally (see "adapter weights" above).
  - GPU runs: 2-task smoke check Nov 13 (4× L4, 1/2, not a score). 10-task smoke Nov 14: **1/10** (6 empty, 3 failed). Matched control run Nov 14
    (same tree and settings, Khushi's quota): **1/10**, same task. Dev run Nov 14 (RUN-007): **5/30**, logged next to the baseline.
    Branch `khushi/structured-prompt-v1` at `6e5a534`, pushed; draft PR #8.
  - *Proposed controlled comparison (pending Dipin's formal confirmation of the rule-1 exception):*
    - **Control:** `dipin-step-budget-v1` (V2 budget: 4.5 min / 50 tool calls, baseline prompt).
    - **Treatment:** the same folder copied, with only `prompts/system.md` (and the README) changed.
    - Model, adapters, sampling, tools, sub-agent and `eval_config.yaml` are byte-identical to the control.
    - The original 1-minute baseline (2/30) stays as a historical reference only, not V1's comparator.
- **V2, Nov 18 — Anti-looping prompt:** notice repeated actions and change strategy; always submit a best-effort diff before running out of steps.
  *Built instead as a single-mechanism time-awareness prompt (`variants/khushi-anti-looping-v2/`, local branch `khushi/anti-looping-v2`: iteration 1 `cfec23d`,
  iteration 2 `af977ad`). Smoke 2/10 and 1/10 vs control 1/10. Recurring status checks never happened, so it's closed as a negative result (rule 7). See `docs/v2_time_awareness_analysis.md`.*
- **V3 (optional):** a prompt targeting the most common failure type in the error analysis.

**Other:** keeps the log complete; per-failure-type results for the report; reviews Poushali.

**Read:** [3] SWE-Protégé, [4] SWE-Master, [11] Survey, [6] Category-aware experts.

**Depends on:** baseline run logs from Sarvesh (Nov 10). *(Baseline dev run logs received from Dipin, Nov 12.)*

### Poushali Deb Purkayastha — Skills & tools

**Setup:**
- [ ] **Nov 9–11:** Confirm exactly which tools and skill formats `agent.yaml` accepts; list the built-in harness tools; share with the team by Nov 11.

**Variants:**
- **V1, Nov 15 — Skills pack:** practical know-how: run only the related pytest tests, write a minimal reproduction, keep diffs small.
- **V2, Nov 20 — Test-runner tool:** an `agent_tool` that runs only the related tests and returns a short failure summary instead of full output.
- **V3 (optional):** code-search skill that uses the provided `graphs/` or `embeddings/` data to suggest likely files.

**Other:** reviews Bhoomika.

**Read:** [9] Codebase-Memory, [8] LARGER, [7] RepoAtlas.

### Bhoomika Lnu — LoRA fine-tuning (highest risk: start today)

**Setup:**
- [x] **Go / no-go by Nov 12:** confirm the adapter format the harness accepts for the 31B model; train a tiny adapter for a few steps and confirm it loads and runs; estimate GPU hours. If it isn't feasible, tell Dipin and switch to putting curated successful runs into the prompt as examples.
  *(Nov 14: **GO**. A tiny QLoRA adapter trained on bf16 31B (Kaggle L4x4) loaded on the QAT model in the harness, all requests routed to `main_lora`, no errors (2-task load test, not a score). V1 training ≈ 2–3 h of quota. Details and Kaggle setup notes: `lora/README.md`.)*

**Variants:**
- **V1, Nov 17 — LoRA on reference patches:** train on `train.txt` tasks only (never `dev.txt`); attach the adapter to the patch-writing agent.
- **V2, Nov 22 — LoRA on curated agent runs:** train on successful runs from the team log, dropping runs with many failed retries; compare held-out loss before spending a submission.

**Other:** reviews Dipin.

**Read:** [13] LoRA, [10] Trajectory curation (error-retry rate is the best quality filter; held-out loss is a cheap check), [5] Open-SWE-Traces.

**Depends on:** V2 only: successful runs in the team log (from about Nov 14).

## Who waits on whom

- Everyone needs Sarvesh's run guide (Nov 10) and Dipin's harness (Nov 12). Until then: join the Kaggle team, read your papers, and draft V1 on the sample agent.
- Khushi's error analysis needs the baseline logs (Nov 10). *(Received Nov 12; analysis done.)*
- Bhoomika's V2 needs successful runs in the log (from about Nov 14).
- The combined agent (Nov 23) uses everyone's best variant.
- Nobody else waits on anybody.

## Submission calendar (1 slot per day)

| Date | Who | Submission |
|---|---|---|
| Tue Nov 10 | Sarvesh | Baseline (unmodified sample agent) |
| Wed Nov 11 | Spare | Early variant if someone is ready |
| Thu Nov 12 | Spare | Early variant if someone is ready |
| Fri Nov 13 | Khushi | V1 Structured loop prompt *(being rescheduled; new date to agree with Dipin)* |
| Sat Nov 14 | Sarvesh | V1 Sampling settings |
| Sun Nov 15 | Poushali | V1 Skills pack |
| Mon Nov 16 | Dipin | V1 Output trimming |
| Tue Nov 17 | Bhoomika | V1 LoRA on reference patches |
| Wed Nov 18 | Khushi | V2 Anti-looping prompt |
| Thu Nov 19 | Sarvesh | V2 Best-of-N attempts |
| Fri Nov 20 | Poushali | V2 Test-runner tool |
| Sat Nov 21 | Dipin | V2 Step and time budget |
| Sun Nov 22 | Bhoomika | V2 LoRA on curated agent runs |
| Mon Nov 23 | Dipin | Combined agent |
| Tue Nov 24 | Dipin | Buffer / **freeze** |
| Nov 25 – Dec 2 | Anyone | Optional V3 variants and final tuning |

Not ready on your date? Take a spare day and tell Dipin.

## Key dates

- **Nov 22:** everyone sends their report section, contribution-table row and one slide to the group's report editor and slide owner.
- **Nov 24:** freeze. Kaggle screenshots for the report.
- **Nov 25:** Kaggle entry and team-merge deadline.
- **Nov 29:** full rehearsal (all 9).
- **Dec 1:** presentation and report (all 9). Everyone submits the peer review form.
- **Dec 2:** final Kaggle deadline. Dipin picks our 2 final submissions (by 3:59 pm Pacific).

## References (numbered as in the proposal)

1. Google – The Gemma 4 Developer Agent Competition, Kaggle, 2026.
2. Gemma Team, Gemma 4 technical report, arXiv:2607.02770.
3. Kon et al., SWE-Protégé, arXiv:2602.22124.
4. Song et al., SWE-Master, arXiv:2602.03411.
5. Ahmad et al., Open-SWE-Traces, arXiv:2606.16038.
6. Zhao et al., Category-aware iterative expert training, arXiv:2609.23377.
7. Zhang et al., RepoAtlas, arXiv:2609.16936.
8. Hu et al., LARGER, arXiv:2605.16352.
9. Vogel et al., Codebase-Memory, arXiv:2603.27277.
10. Han, Trajectory data curation for LoRA fine-tuning of code agents, arXiv:2607.17205.
11. Jiang, Lo and Liu, Agentic software issue resolution survey, arXiv:2512.22256.
12. Jimenez et al., SWE-bench, ICLR 2024.
13. Hu et al., LoRA, ICLR 2022.
