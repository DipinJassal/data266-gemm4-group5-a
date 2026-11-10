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

## Status (last updated Nov 9, 2026)

**Done**
- Repo created and public: https://github.com/DipinJassal/data266-gemm4-group5-a. Sarvesh, Poushali and Khushi invited (write access).
- Kaggle CLI installed on Dipin's Mac; competition data downloaded into `data/` (git-ignored; snapshots, 21.5 GB, not yet downloaded).
- Rules section above updated from Kaggle's official `HARNESS_README.md`.
- `harness/make_splits.py` → `harness/splits/`: **dev 30** (fastapi 15, rich 11, requests 3, httpx 1), **train 99**,
  **smoke 10** (a subset of train, so tuning on smoke never touches dev). Deterministic (seed 266).
- `harness/validate.py`: offline pre-check of a variant folder (rule 6 items) and `--zip` to build `submission.zip`.
- `harness/run_kaggle.py` + `kaggle_runner.py` + `summarize.py`: score a variant on a split in a Kaggle GPU kernel
  from your laptop, then get per-task pass/fail, time, tool calls and a baseline comparison. Tested offline (dry run, fake results);
  **not yet run on a real Kaggle GPU**.

**Next for Dipin**
- [ ] Invite Bhoomika to the GitHub repo (need Bhoomika's GitHub username).
- [ ] Create the Kaggle team, invite all 4, agree the team name with the other team.
- [ ] Check the items marked *(Rules tab)* above on the Kaggle Rules page and post the rules to the team.
- [ ] First real harness run (2 smoke tasks) once `baseline/` has the sample agent, to confirm the GPU type
  (`NvidiaL4` gives 4 GPUs?), the input paths and the result fields. Fix anything that breaks, then announce the harness to the team.

**Next for others**
- [ ] **Sarvesh:** put the unmodified `sample_submission/` into `baseline/` (it's in the competition data; see "How to run"). The harness needs it.
- [ ] **Everyone:** install the Kaggle CLI, accept the competition rules, save your API token (see `harness/README.md`), so you can run the harness on your own GPU quota.

**Findings the team needs to know**
- **Everyone:** the official local evaluator is `swegemma` (not on PyPI; installed from the Kaggle dataset
  `metric/gemma-4-developer-agent-wheelhouse` inside a Kaggle notebook). Running the agent needs an L4×4 GPU, so scored runs happen on Kaggle, not laptops.
  The official "Getting Started" notebook (`ryanholbrook/getting-started-gemma-4-developer-agent`) is the reference.
- **Sarvesh:** the sample `eval_config.yaml` caps each task at **1 minute and 10 tool calls**, so the unmodified baseline will likely score very low.
  Submit it unchanged (it's the baseline), but note this in `docs/baseline_profile.md`.
- **Poushali:** the allowed tools and skill format are listed in the Rules section above (from `data/HARNESS_README.md` §2 and §6), which covers most of the Nov 11 setup task.
- **Bhoomika:** the sample adapters are dummies (rank 4, layer 0 only, `q_proj`/`o_proj`). Limits: `.safetensors`, rank ≤ 128, whole zip < 3 GiB (§3.4 of the harness doc).
- **Dipin (V2):** the per-task budget lives in `eval_config.yaml`; 12 h / ~120 tasks leaves about 5 minutes of agent time after setup.

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
  Results go to `harness/runs/`; details in `harness/README.md`. *(Not yet confirmed on a real GPU run; see Status.)*

## Individual tasks

### Dipin Jassal — captain, starts the project, Context & time budget

**Setup (starting today):**
- [ ] **Nov 9–10:** Confirm the rules on the Kaggle Rules tab and post them to the team. Create the Kaggle team and invite all 4. Agree the team name (`Group_5_a` or `Group_5_b`) with the other team. *(Rules mostly confirmed from the official harness doc; Rules-tab items and Kaggle team still open.)*
- [x] **Nov 10:** Create this repo with the layout above and the README template. *(Done Nov 9; public on GitHub.)*
- [ ] **Nov 12:** Local harness, with `smoke.txt` (10 tasks), `dev.txt` (30 tasks, covering all 4 repos) and `train.txt` (the other 99). *(Splits ✅, validator ✅, Kaggle runner + summary written ✅, first real GPU run ⏳.)*

**Variants:**
- **V1, Nov 16 — Output trimming:** cap long tool outputs (file reads, test logs) and summarize older turns.
- **V2, Nov 21 — Step and time budget:** per-task step cap sized to about 6 minutes, with a forced submission of the best diff so far.
- **Combined agent, Nov 23:** merge everyone's best variant into one `agent.yaml`, and add a patch-hygiene check (reject empty or non-applying diffs, strip stray debug files).

**Other:** owns the submission calendar and slot swaps; reviews Sarvesh; picks the 2 final submissions by Dec 2; sends Kaggle evidence (team name, members, submission history, scores, best result, screenshots) for the report on Nov 24 and after Dec 2.

**Read:** [12] SWE-bench, [7] RepoAtlas, [9] Codebase-Memory, [3] SWE-Protégé.

### Sarvesh Reshimwale — starts the project, Sampling & multiple attempts

**Setup (starting today):**
- [ ] **Nov 9–10:** Get the sample agent running end to end in a Kaggle notebook. Write `docs/run_guide.md` (how to run a few tasks, how to zip and submit).
- [ ] **Nov 10:** Submit the baseline. Share its run logs with Khushi.
- [ ] **Nov 11–12:** Write `docs/baseline_profile.md`: average time and turns per task, slowest tasks, longest tool outputs.

**Variants:**
- **V1, Nov 14 — Sampling settings:** small sweep of temperature / top-p and thinking mode on vs off on the smoke set; submit the best.
- **V2, Nov 19 — Best-of-N attempts:** several attempts, keep the patch that passes the agent's own reproduction test, stop early on a pass. If `agent.yaml` can't express this, use "if your test fails, retry once with a different approach."
- **V3 (optional):** max output tokens or step-limit tuning.

**Other:** reviews Khushi.

**Read:** [4] SWE-Master (test-time scaling: 61.4% → 70.8% at 8 attempts), [5] Open-SWE-Traces, [3] SWE-Protégé.

### Khushi Donda — Prompts, team experiment log, error analysis

**Setup:**
- [ ] **Nov 10:** Team experiment log (shared sheet) with columns: variant, owner, one-line change, smoke time, dev score, Kaggle score, status, notes.
- [ ] **Nov 11–12:** `docs/error_analysis.md`: label every baseline failure as wrong file found, right file but wrong fix, broke other tests, timeout or looping, or empty/invalid diff. Share the counts.

**Variants:**
- **V1, Nov 13 — Structured loop prompt:** reproduce → localize → plan → edit → test → submit, with a short checklist before submitting.
- **V2, Nov 18 — Anti-looping prompt:** notice repeated actions and change strategy; always submit a best-effort diff before running out of steps.
- **V3 (optional):** a prompt targeting the most common failure type in the error analysis.

**Other:** keeps the log complete; per-failure-type results for the report; reviews Poushali.

**Read:** [3] SWE-Protégé, [4] SWE-Master, [11] Survey, [6] Category-aware experts.

**Depends on:** baseline run logs from Sarvesh (Nov 10).

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
- [ ] **Go / no-go by Nov 12:** confirm the adapter format the harness accepts for the 31B model; train a tiny adapter for a few steps and confirm it loads and runs; estimate GPU hours. If it isn't feasible, tell Dipin and switch to putting curated successful runs into the prompt as examples.

**Variants:**
- **V1, Nov 17 — LoRA on reference patches:** train on `train.txt` tasks only (never `dev.txt`); attach the adapter to the patch-writing agent.
- **V2, Nov 22 — LoRA on curated agent runs:** train on successful runs from the team log, dropping runs with many failed retries; compare held-out loss before spending a submission.

**Other:** reviews Dipin.

**Read:** [13] LoRA, [10] Trajectory curation (error-retry rate is the best quality filter; held-out loss is a cheap check), [5] Open-SWE-Traces.

**Depends on:** V2 only: successful runs in the team log (from about Nov 14).

## Who waits on whom

- Everyone needs Sarvesh's run guide (Nov 10) and Dipin's harness (Nov 12). Until then: join the Kaggle team, read your papers, and draft V1 on the sample agent.
- Khushi's error analysis needs the baseline logs (Nov 10).
- Bhoomika's V2 needs successful runs in the log (from about Nov 14).
- The combined agent (Nov 23) uses everyone's best variant.
- Nobody else waits on anybody.

## Submission calendar (1 slot per day)

| Date | Who | Submission |
|---|---|---|
| Tue Nov 10 | Sarvesh | Baseline (unmodified sample agent) |
| Wed Nov 11 | Spare | Early variant if someone is ready |
| Thu Nov 12 | Spare | Early variant if someone is ready |
| Fri Nov 13 | Khushi | V1 Structured loop prompt |
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
