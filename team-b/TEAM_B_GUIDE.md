# Team B Guide — DATA 266 Group 5, Gemma 4 Developer Agent (Kaggle team of 4, Team B)

This file tells every Team B member what the project is, how Team B's part of the repo is organized,
and who owns what. Read it before making changes. Keep the Status section up to date.

## Project in one paragraph

We are building an autonomous software-engineering agent for the Kaggle **Gemma 4 Developer Agent** competition.
Given a Python repository and a bug report, the agent finds the problem, edits the code and submits a patch.
Kaggle runs hidden tests on each patch; the score is the percentage of issues resolved. We start from the
**sample agent** and improve it **one change at a time**, so the final report can show which changes helped
and which failed. Our group of 9 is split into two Kaggle teams because Kaggle caps teams at 5.
**This folder (`team-b/`, branch `group5-team-b`) is the team of 4.** Team A (team of 5) works on `main` in the same repo.
The report, presentation and peer review are shared by all 9.

## How Team B relates to Team A

| Shared with Team A (do not change on your own) | Team B's own |
|---|---|
| The model: `gemma-4-31b-it-qat-w4a16-ct` | Kaggle team `GROUP_PROGRAMMING_05_b` and its 1 submission per day |
| Harness scripts in `harness/` (Dipin's) | Variants in `team-b/variants/` |
| Task lists `harness/splits/{dev,train,smoke}.txt` | Team B baseline submission and score on Kaggle |
| Experiment-log columns | Team B experiment log `team-b/docs/experiment_log.csv` |
| Report, slides, peer review, Kaggle evidence for both teams | Team B combined agent `team-b/combined/` |
| Paper references (numbered below) | Team B calendar, reviews and final 2 picks |

Team B uses Team A's harness and task lists so both teams' scores are comparable. Never edit Team A's folders
(`baseline/`, `variants/`, `combined/`, `harness/`). If the harness needs a fix, tell Dipin.

## Competition rules

Source: Kaggle's official `HARNESS_README.md` (see Team A's root guide file, Rules section).

- **One base model per submission**, shared by every agent and sub-agent: `gemma-4-31b-it-qat-w4a16-ct`.
  LoRA adapters are optional (`.safetensors`, rank ≤ 128). Team B does not plan LoRA (Team A covers it).
- A submission is a **`submission.zip` with `agent.yaml` at the root**, declarative YAML only (no Python entry point).
  Tools: only the 9 harness tools (`run_command`, `submit_patch`, `get_status`, `read_file`, `edit_file`, `write_file`,
  `get_code_neighbors`, `search_similar_code`, `get_code_subgraph`) or `agent_tool` sub-agents. Skills are folders with `SKILL.md`.
  Allowed file types: `.yaml .yml .md .txt .py .json .safetensors`. No symlinks, no paths outside the root, total < 3 GiB.
- **12-hour runtime** for ~120 hidden tasks → about **6 minutes per task**. Per-task budget lives in `eval_config.yaml`
  (`max_time_minutes`, `max_tool_calls`, `max_turns`).
- Context window **32,768 tokens**. Sandbox: offline, 4 GiB RAM, 2 vCPUs. Output caps (5,000 chars per command,
  150 lines per `read_file`) and older-turn summarizing are fixed by Kaggle.
- A task counts only if the hidden tests pass. Changes to test files are stripped before scoring.
- **1 submission per team per day.** Kaggle's day resets at 4:00 pm Pacific. Up to 2 final submissions (picked by Dec 2).
- Hidden tasks come from **private repos**, not the 4 public ones (FastAPI, Rich, Requests, HTTPX).

## Compute

- Scored runs need an **L4 ×4 GPU**, so they run on **Kaggle**, launched from your laptop with `harness/run_kaggle.py`.
  Each member uses **their own Kaggle GPU quota** (it is not pooled; L4 time counts double).
- **Colab or your laptop** is for work that needs no GPU: EDA of `tasks.jsonl`, offline retrieval checks,
  log/trace analysis, charts, `validate.py`.
- Budget per variant: 1–2 smoke runs (~2 quota-hours each) + 1 dev run (~5 quota-hours) ≈ **7–9 quota-hours**.
  Iterate on smoke; run dev once the variant is final.

## Team B

| Member | Role | Area (2 variants each) | Reviewed by |
|---|---|---|---|
| **Ashmitha** | Kaggle team, baseline, experiment log, Kaggle evidence, combined agent | Lead & evaluation (patch hygiene; combined agent) | Naveen |
| **Parth** | Multi-agent owner | Multi-agent (analyzer + coder; coder + critic) | Ashmitha |
| **Ishan** | Task data EDA (G.2) | Retrieval / code graph (graph-first localization; graph expansion) | Parth |
| **Naveen** | Team B error analysis | Testing & verification (reproduce-first; regression check) | Ishan |

Review rotation: Ashmitha → Parth → Ishan → Naveen → Ashmitha (each reviews the next; nobody approves their own variant).

## Variants and folders

Every variant is `team-b/variants/base` plus one change. Folder names describe the idea; V1/V2 is tracked here.

| Owner | Area | V1 (folder) | V2 (folder) |
|---|---|---|---|
| Ashmitha | Lead & evaluation | `patch-hygiene` | combined agent (`team-b/combined/`) |
| Parth | Multi-agent | `analyzer-plan` | `diff-critic` |
| Ishan | Retrieval / code graph | `graph-localize` | `graph-expand` |
| Naveen | Testing & verification | `repro-first` | `regression-check` |

`base` is the starting point, not a variant. Phase 2 tuning runs use `tune-<what>`.

## Decisions (read this first)

These are settled. If something here is unclear, ask in the team chat before starting work.

| Topic | Decision |
|---|---|
| Baseline agent files | **Reuse** `baseline/` from this repo. It is Kaggle's sample agent, unchanged. Never edit it or copy it into `team-b/`. |
| Local dev score of the baseline | **Reuse** Team A's run: **2/30 (6.7%)** on Nov 10. Team B does not re-run it. |
| Kaggle baseline submission | **Team B's own.** Submitted once on Team B's Kaggle team, with a screenshot. This is the official Team B baseline for the report (G.2) and for improvement over baseline (G.6 Part B). |
| Starting agent for every variant | `team-b/variants/base/`: Team A's budget fix (4.5 min / 50 tool calls instead of 1 min / 10), copied unchanged. "One change" is measured against it, and the report says so. |
| Harness and task lists | Shared with Team A (`harness/`, `harness/splits/`). Never edited on this branch; harness problems go to Dipin. |
| How work is organised | **Phase 1** (Nov 13–23): finish the first model with the group plan. **Phase 2** (Nov 24–30): everyone is free to tune it. Rules below. |

## Phase 1 — finish the first model (Nov 13 – Nov 23)

Each member builds and submits their 2 single-change variants on their calendar date (course rule: every member
develops 2–3 versions and submits them to the leaderboard). The best variants are then merged into the
**combined agent**, submitted Nov 23. That combined agent is Team B's first model.

## Phase 2 — free tuning (Nov 24 – Nov 30)

After the first model has run on Kaggle, any member may tune it to get better results. To keep results usable in
the report:

1. **Start from the latest combined agent.** Copy `team-b/combined/` into `team-b/variants/tune-<what>/`
   (19 characters or less), on a branch `b/tune-<what>`.
2. **One change per tuning run** where possible (prompt wording, budget, sampling, adding or removing one variant),
   so the report can link each gain to a change.
3. **Log every run** in `team-b/docs/experiment_log.csv`, including runs that made things worse.
4. **Book the Kaggle slot the day before** in the team chat. There is 1 submission per day for the whole team.
   First come, first served; nobody takes two days in a row while others are waiting.
5. **Smoke first, dev once.** Never tune on the 30 dev tasks.
6. **Tuning means prompts, settings and sub-agents.** No LoRA training (Team A covers LoRA; too slow to start now).
7. **Report cutoff: Nov 30.** Results after that do not go into the report or slides. Dec 1–2 is only for picking the
   2 final submissions.
8. If a tuning run beats the combined agent on dev, it becomes the new combined agent: open a PR that updates
   `team-b/combined/` and note it in the log.

## Status (last updated Nov 13, 2026)

**Done**
- Plan agreed (see `TEAM_B_PLAN.md`).

**Next**
- [ ] Ashmitha: create Kaggle team `GROUP_PROGRAMMING_05_b`, invite Parth, Ishan, Naveen.
- [ ] Ashmitha: ask Dipin for write access, create branch `group5-team-b`, add `team-b/` skeleton.
- [ ] Everyone: join the competition, phone-verify Kaggle, install Kaggle CLI, save API token, accept invites.
- [ ] Ashmitha: submit Team B baseline (unchanged sample agent) and log it.

**Findings the team needs to know**
- **Adapter weights are not in git.** `*.safetensors` is git-ignored, so on a fresh clone `validate.py` fails every
  agent (Team A's `baseline/` too) with "adapter ... missing adapter_model.safetensors". After downloading the
  competition data, copy Kaggle's dummy weights into each variant folder you build (they stay untracked):
  `cp data/sample_submission/adapters/main_lora/adapter_model.safetensors team-b/variants/<folder>/adapters/main_lora/`
  and the same for `tool_lora`. Check the exact path in `data/sample_submission/` first.
- The sample agent already has an `agent_tool` sub-agent (`sub_agents/code_analyzer.yaml`, prompt `prompts/analyzer.md`).
  Parth's analyzer variant changes how and when it is used; it does not add it from scratch.
- The sample system prompt already says: never edit tests, run only targeted tests, check `patch_size > 0`.
  Patch hygiene and regression-check variants must add something beyond that (scratch-file cleanup, compile check,
  running the existing tests of the changed module).
- From Team A: in the baseline, 20/30 dev tasks produced no patch (cut off at 1 minute); the agent often had found the right file.
- From Team A: the agent re-reads the same lines (looping), and one patch contained a stray `repro.py`. Both matter for patch hygiene.
- Team A error analysis: `docs/error_analysis.md` on `main` (Khushi). Use its failure labels.

## Folder layout (Team B)

```
team-b/
  TEAM_B_GUIDE.md               This file (Ashmitha)
  README.md                     Short overview + how to run (Ashmitha)
  docs/
    competition_summary.md      G.1: task, inputs/outputs, metric, rules, constraints (Ashmitha)
    task_eda.md                 G.2: tasks.jsonl and repo analysis, charts (Ishan)
    retrieval_eval.md           Offline file-hit@k results (Ishan)
    multi_agent_notes.md        How sub-agents are declared and what they cost (Parth)
    error_analysis_b.md         G.2: failure labels for Team B runs (Naveen)
    experiment_log.csv          Every run, including failures (everyone; Ashmitha keeps it complete)
  notebooks/
    task_eda.ipynb              Colab/laptop, no GPU (Ishan)
    retrieval_eval.ipynb        Colab/laptop, no GPU (Ishan)
    results_charts.ipynb        Score-over-time chart for G.4 (Ashmitha)
  variants/
    _template/README.md         3-line README template
    base/                       Starting point for all Team B variants (not a variant)
    patch-hygiene/              V1 (Ashmitha)
    analyzer-plan/              V1 (Parth)
    diff-critic/                V2 (Parth)
    graph-localize/             V1 (Ishan)
    graph-expand/               V2 (Ishan)
    repro-first/                V1 (Naveen)
    regression-check/           V2 (Naveen)
  combined/                     V2: Team B combined agent (Ashmitha)
  results/                      Small run summaries (summarize.py --csv output), committed by each owner
  report/
    sections/<area>.md          One section per area: lead-evaluation (Ashmitha), multi-agent (Parth),
                                retrieval (Ishan), verification (Naveen)
    kaggle_evidence/            Submission history screenshots (Ashmitha)
  slides/<area>.md              One slide per area, same owners as the report sections
```

Variant folder names: `<short-name>` with **no version suffix**; whether a folder is its owner's V1 or V2 is
tracked in the "Variants and folders" table. Add `-2`, `-3` only when the same idea is revised
(e.g. `diff-critic-2`). **At most 19 characters** (the harness cuts Kaggle kernel names to
50 characters; longer names make smoke and dev runs share one kernel and overwrite each other). Each variant `README.md` has exactly three lines:
1. **What changed** (one change from the base)
2. **Why** (which failure type it targets)
3. **Source** (which paper, by reference number below)

## Rules for every change

1. **One change per variant**, relative to `base`. Only `team-b/combined/` mixes changes.
2. **Never edit Team A's folders or another member's variant folder.** Copy the base into a new folder instead.
3. **Never train or tune on `harness/splits/dev.txt` tasks.** Tune on smoke/train; report dev once per variant.
4. **Keep changes general.** No hard-coded paths, file names or logic for FastAPI, Rich, Requests or HTTPX.
5. **Stay inside the runtime budget.** Average time per task on smoke must stay under about 6 minutes.
6. **Before review:** smoke runs with no crashes → dev score logged next to the base → `validate.py` passes → zip has
   `agent.yaml` at the root → only allowed tools used.
7. **Log every run** in `team-b/docs/experiment_log.csv`, including failures. A variant below the base can still be
   submitted; documented failures are required by the course (G.3).
8. **Submit only through the Team B Kaggle team**, on your calendar date, after reviewer approval the day before.
9. **Git:** work on a short branch `b/<variant>`, open a PR into `group5-team-b`. Never push to `main`.

## How to run

All commands run from the repo root.

- Check a variant and build its zip (no GPU): `python harness/validate.py team-b/variants/<folder> --zip submission.zip`
- Quick test (2 tasks): `python harness/run_kaggle.py team-b/variants/<folder> smoke --max-tasks 2`
- Smoke (10 tasks): `python harness/run_kaggle.py team-b/variants/<folder> smoke`
- Dev score (30 tasks): `python harness/run_kaggle.py team-b/variants/<folder> dev`
- Start now, fetch later: add `--no-wait`, then `python harness/run_kaggle.py --fetch team-b/variants/<folder> dev`
- Log row: `python harness/summarize.py --csv ...` (see `harness/README.md`), paste into `team-b/docs/experiment_log.csv`.

## Individual tasks

Full task lists are in `TEAM_B_PLAN.md`. Summary:

### Ashmitha — Lead & evaluation
- Setup: Kaggle team, branch + skeleton, baseline submission, the base agent (reuse Team A's scores), experiment log, `competition_summary.md`.
- **V1, Nov 16 — Patch hygiene:** prompt checklist before `submit_patch`: no empty diff, delete scratch files
  (`repro.py`, debug prints), re-read edited lines, `python -m py_compile` on changed files, never edit tests.
- **V2, Nov 23 — Combined agent:** merge the best Team B variants into one `agent.yaml`.
- Other: calendar and slot swaps, Kaggle evidence and score-over-time chart, pick 2 finals by Dec 2, report liaison.
- Read: [12] SWE-bench, [4] SWE-Master, [6] Category-aware experts.

### Parth — Multi-agent
- **V1, Nov 17 — Analyzer + coder:** an `agent_tool` analyzer sub-agent reads the issue and code and returns
  files to change + a short plan; the main agent edits.
- **V2, Nov 20 — Coder + critic:** a critic sub-agent reviews the diff against the issue, one round of feedback.
- V3 (optional): category-routed specialists (bug fix vs feature request).
- Read: [3] SWE-Protégé, [6] Category-aware experts, [11] Survey.

### Ishan — Retrieval / code graph, task EDA
- Setup: `task_eda.md` (G.2) and offline retrieval check (file-hit@5 on train tasks, Colab/laptop).
- **V1, Nov 18 — Graph-first localization:** agent calls `search_similar_code` / `get_code_neighbors` with issue
  identifiers before reading files.
- **V2, Nov 21 — Graph expansion:** from the top matches, add callers, callees and related tests via
  `get_code_subgraph`, within a fixed size budget.
- Read: [8] LARGER, [7] RepoAtlas, [9] Codebase-Memory.

### Naveen — Testing & verification, error analysis
- Setup: build on Team A's `docs/error_analysis.md` (no new base run); `error_analysis_b.md` adds labels only for Team B variant runs.
- **V1, Nov 15 — Reproduce-first skill:** write a minimal failing reproduction, fix, rerun it, delete it.
- **V2, Nov 19 — Regression check:** before submit, run only the related existing tests (`pytest -q -x --tb=short <file>`)
  and fix any newly broken test. Coordinate with Poushali (Team A test-runner) to avoid duplicating her design.
- Read: [3] SWE-Protégé, [4] SWE-Master, [12] SWE-bench.

## Submission calendar (Team B, 1 slot per day)

| Date | Who | Submission |
|---|---|---|
| Fri Nov 13 | Ashmitha | Baseline (unmodified sample agent) |
| Sat Nov 14 | Ashmitha | Base agent (budget fix) |
| Sun Nov 15 | Naveen | V1 Reproduce-first skill |
| Mon Nov 16 | Ashmitha | V1 Patch hygiene |
| Tue Nov 17 | Parth | V1 Analyzer + coder |
| Wed Nov 18 | Ishan | V1 Graph-first localization |
| Thu Nov 19 | Naveen | V2 Regression check |
| Fri Nov 20 | Parth | V2 Coder + critic |
| Sat Nov 21 | Ishan | V2 Graph expansion |
| Sun Nov 22 | Spare | Resubmit / late variant. **Report sections, contribution rows, slides due** |
| Mon Nov 23 | Ashmitha | Combined agent |
| Tue Nov 24 | Ashmitha | Buffer / **freeze**. Kaggle screenshots |
| Wed Nov 25 | Spare | Kaggle entry deadline |
| Nov 24 – Nov 30 | Anyone (booked a day ahead) | Phase 2 tuning on the combined agent (Nov 24 is first used as a buffer if the combined agent needs a resubmit) |
| Dec 1 – Dec 2 | Ashmitha | Pick the 2 final submissions only |

Not ready on your date? Take the next spare and tell Ashmitha.

## Key dates

- **Nov 22:** report section, contribution row and one slide to the group's report editor and slide owner.
- **Nov 24:** freeze; Kaggle screenshots.
- **Nov 25:** Kaggle entry and team-merge deadline.
- **Nov 30:** last day for tuning results that go into the report and slides.
- **Nov 29:** full rehearsal (all 9). **Dec 1:** presentation and report. Everyone submits the peer review form.
- **Dec 2:** final Kaggle deadline; Ashmitha picks Team B's 2 final submissions (by 3:59 pm Pacific).

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
