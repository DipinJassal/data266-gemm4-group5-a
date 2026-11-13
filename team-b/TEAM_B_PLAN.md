# Team B Plan — DATA 266 Group 5, Gemma 4 Developer Agent

Team: **GROUP_PROGRAMMING_05_b** (Kaggle team of 4) · Members: Ashmitha, Parth, Ishan, Naveen
Period: Nov 13 – Nov 25, 2026 (Kaggle entry deadline), then free tuning to Nov 30 (report cutoff); Dec 2 is the final Kaggle deadline.
Report and presentation are shared with Team A (Dipin, Sarvesh, Khushi, Poushali, Bhoomika).

---

## 1. What we are doing, in one minute

- Kaggle gives a fixed model (Gemma 4 31B) and a **sample agent**: `agent.yaml` + prompts + `eval_config.yaml`.
- The agent gets a Python repo + bug report and must submit a patch. Score = % of bugs whose hidden tests pass.
- We do **not** train a new model. Each of us builds **2 variants of the agent**, each changing **one thing**
  (prompt, sub-agents, skills, tool usage, settings). We test each variant, submit it to Kaggle, and write up
  what helped and what failed.
- At the end, Ashmitha merges the best changes into one **combined agent** (Team B's "first full model").
- After that (Nov 24 – Nov 30), everyone is free to tune the combined agent for a better score. This matches
  Team A's approach: "finish the first model with the plan, run it on Kaggle, then everyone tunes."

## 2. Two phases

| Phase | Dates | Goal | Output |
|---|---|---|---|
| **Phase 1 — Build the first model** | Nov 13 – Nov 23 | Baseline + 7 single-change variants + combined agent | 10 Kaggle submissions, experiment log, report sections |
| **Phase 2 — Tune** | Nov 24 – Nov 30 | Improve the combined agent (budget, prompt wording, which variants to include) | Best score, 2 final picks |

Phase 2 is free tuning, with the rules in `TEAM_B_GUIDE.md` (Phase 2 section): one change per run, log every run,
book the Kaggle slot a day ahead, never tune on dev, results after Nov 30 do not go into the report.

What Team B reuses and what it does itself is listed in `TEAM_B_GUIDE.md` under "Decisions".

## 3. How the course rubric (35 marks) maps to Team B work

| Rubric item | Marks | What earns it | Owner in Team B |
|---|---|---|---|
| G.1 Competition understanding & setup | 5 | Task, inputs/outputs, metric, rules, constraints written up; baseline submitted | Ashmitha (`competition_summary.md`, baseline) |
| G.2 Data / environment processing & baseline | 5 | EDA of tasks/repos that **informs design**; baseline score with evidence | Ishan (`task_eda.md`), Naveen (`error_analysis_b.md`), Ashmitha (baseline) |
| G.3 Improvement & experimentation | 5 | ≥2 strategies compared under the same evaluation; ≥1 failed approach analyzed; complete log | Everyone (2 variants each), Ashmitha (log) |
| G.4 Submissions & tracking | 5 | Regular submissions across the period; score-over-time table/chart; Kaggle evidence | Ashmitha (calendar, chart, screenshots) |
| G.5 Final analysis & presentation | 5 | Full solution, trade-offs, compute limits, lessons, concrete future work; everyone presents | Everyone (own section + slide) |
| G.6 Ranking & improvement vs baseline | 10 | Best Kaggle score; **improvement over our own baseline linked to specific changes** | Ashmitha (combined agent, finals), everyone (variants) |

Course requirement: **every member develops 2–3 architectures and submits them to the leaderboard.** The calendar
gives each member 2 Kaggle slots (Ashmitha: patch hygiene + combined; baseline and the base agent are extra).

## 4. Areas (chosen so Team B does not repeat Team A)

Team A covers: Context & time budget (Dipin), Sampling (Sarvesh), Prompts (Khushi), Skills & tools (Poushali), LoRA (Bhoomika).

| Member | Area | V1 | V2 | Optional V3 (Phase 2) |
|---|---|---|---|---|
| Ashmitha | Lead & evaluation | Patch hygiene | Combined agent | Final tuning of the combined agent |
| Parth | Multi-agent | Analyzer + coder | Coder + critic | Category-routed specialists |
| Ishan | Retrieval / code graph | Graph-first localization | Graph expansion | Retrieval hints in the analyzer (with Parth) |
| Naveen | Testing & verification | Reproduce-first skill | Regression check before submit | Retry once if own test fails |

## 5. Compute: Kaggle vs Colab

| Work | Where | GPU? |
|---|---|---|
| Smoke/dev/Kaggle scoring of any variant | Kaggle (L4 ×4), launched by `harness/run_kaggle.py` from your laptop | Yes, your own quota |
| Building the zip, `validate.py` | Laptop | No |
| Task EDA, retrieval checks, trace analysis, charts | Colab (CPU runtime is enough) or laptop | No |
| Notebook alternative to the harness | Copy of `ryanholbrook/getting-started-gemma-4-developer-agent` on Kaggle (pinned Python 3.12 env) | Yes |

Colab cannot run the official evaluator (`swegemma` comes from a Kaggle dataset) or the 31B model at harness speed,
so all scored runs happen on Kaggle.

**GPU budget per member (quota-hours; L4 counts double):**

| Member | Runs planned | Approx. quota-hours |
|---|---|---|
| Ashmitha | V1 smoke 2 + dev 1, combined smoke 1 + dev 1 (baseline and the base agent reuse Team A's runs) | ~20 over 2 weeks |
| Parth | V1 smoke 2 + dev 1, V2 smoke 2 + dev 1 | ~18 |
| Ishan | V1 smoke 2 + dev 1, V2 smoke 2 + dev 1 | ~18 |
| Naveen | V1 smoke 2 + dev 1, V2 smoke 2 + dev 1 (error analysis reuses Team A's runs) | ~18 |

If Ashmitha runs low, another member runs the combined agent's dev score on their quota. Check your weekly
quota at kaggle.com/settings before starting a dev run.

## 6. Submission calendar (one slot per day, Kaggle day resets 4:00 pm Pacific)

Rule: dev score logged and reviewer approval **the evening before** your slot. Start dev runs with `--no-wait`
at least a day ahead (≈2.5 h run + up to 30 min queue).

| Date | Slot | Other work that day |
|---|---|---|
| Fri Nov 13 | Ashmitha: Baseline | Kickoff call; Kaggle team; branch + skeleton; everyone sets up CLI |
| Sat Nov 14 | Ashmitha: Base agent (budget fix) | Naveen reads Team A's error analysis; Ishan EDA |
| Sun Nov 15 | Naveen: V1 Reproduce-first | Parth/Ishan smoke runs on V1 |
| Mon Nov 16 | Ashmitha: V1 Patch hygiene | Parth dev run (V1) |
| Tue Nov 17 | Parth: V1 Analyzer + coder | Ishan dev run (V1) |
| Wed Nov 18 | Ishan: V1 Graph-first | Naveen dev run (V2) |
| Thu Nov 19 | Naveen: V2 Regression check | Parth dev run (V2) |
| Fri Nov 20 | Parth: V2 Coder + critic | Ishan dev run (V2); Ashmitha drafts combined |
| Sat Nov 21 | Ishan: V2 Graph expansion | Ashmitha combined smoke + dev |
| Sun Nov 22 | Spare | **Report sections, contribution rows, slides due** |
| Mon Nov 23 | Ashmitha: Combined agent | Log, chart |
| Tue Nov 24 | Buffer / freeze | Kaggle screenshots; Phase 2 starts |
| Wed Nov 25 | Spare | Kaggle entry deadline |
| Nov 26 – Nov 30 | Phase 2 tuning slots (booked a day ahead) | Nov 30: report cutoff for tuning results |
| Dec 1 – Dec 2 | Final picks only | Dec 2: Ashmitha picks 2 finals by 3:59 pm Pacific |

Planned Phase 1 submissions: 10 (baseline, the base agent, 7 variants, combined). Spares: Nov 22, 24, 25.

## 7. Detailed to-dos per member

Each variant follows the same 8-step loop (referred to below as **"the variant loop"**):

1. `git checkout group5-team-b && git pull` then `git checkout -b b/<variant>`
2. `cp -r team-b/variants/base team-b/variants/<short-name>`
3. Make **one** change; fill in the 3-line README (What changed / Why / Source).
4. `python harness/validate.py team-b/variants/<folder> --zip submission.zip` (no GPU).
5. Quick test: `python harness/run_kaggle.py team-b/variants/<folder> smoke --max-tasks 2` (no crashes?).
6. Smoke: `... smoke` (10 tasks). Check avg time per task < 6 min. Iterate on smoke only.
7. Dev once final: `... dev --no-wait`, then `--fetch`. Log the row in `team-b/docs/experiment_log.csv`.
8. Commit, push, open PR into `group5-team-b`, tag your reviewer. After approval, Ashmitha (or you) submits on your date.

---

### Ashmitha — Lead & evaluation

**Setup (Nov 13–14)**
- [ ] Create Kaggle team `GROUP_PROGRAMMING_05_b`; invite Parth, Ishan, Naveen; confirm all 4 joined.
- [ ] Message Dipin: Team B uses Team A's harness and splits; ask for write access to the repo for all 4; confirm
      the team naming (`_a` / `_b`) and the "build on budget-fixed base" decision.
- [ ] Create branch `group5-team-b` from `main`; add the `team-b/` skeleton (this file, `TEAM_B_GUIDE.md`, `README.md`,
      `variants/_template/`, empty `docs/experiment_log.csv` with the shared columns).
- [ ] Download competition data once: `kaggle competitions download gemma-4-developer-agent -f tasks.jsonl -p data`
      (+ `HARNESS_README.md`); share `tasks.jsonl` path with Ishan.
- [ ] **Baseline:** zip `baseline/` unchanged with `validate.py`, submit on Nov 13. Record public score + screenshot.
      Do not re-run it on dev (Team A's dev number 2/30 is the group's dev baseline).
- [ ] **Base v0:** copy `variants/dipin-step-budget-v1` to `team-b/variants/base/`, README credits
      Dipin. Do **not** re-run it: reuse Dipin's smoke (2/10) and dev scores, after checking the folder is byte-identical
      (`diff -r variants/dipin-step-budget-v1 team-b/variants/base`, README aside). Only run it yourself
      if Dipin's dev score is still missing by Nov 15. Submit to Kaggle on Nov 14 (costs a daily slot, no GPU quota).
- [ ] Write `team-b/docs/competition_summary.md` (G.1): task, inputs (repo snapshot, issue text, code graphs,
      embeddings), output (patch), metric, 9 tools, limits (32K context, 6 min/task, 12 h, offline sandbox,
      4 GiB RAM), submission format, 1/day, private hidden repos.
- [ ] Set up the review rotation and post the calendar in the team chat.

**V1 — Patch hygiene (smoke by Nov 15, slot Nov 16)**
- [ ] In the base system prompt, add a "before you call `submit_patch`" checklist:
      diff is non-empty; only source files changed (no tests, no `repro.py`, no scratch files); delete any files you
      created for testing; run `python -m py_compile` on every changed file; re-read the edited lines once.
- [ ] Run the variant loop. In the README: What = pre-submit checklist; Why = empty / dirty diffs (Team A finding);
      Source = [12] SWE-bench.
- [ ] Compare: count of empty patches and stray files vs the base agent, not just the score.

**Experiment log and evidence (ongoing)**
- [ ] Keep `experiment_log.csv` complete every day: variant, owner, one-line change, smoke score, smoke avg time,
      dev score, Kaggle score, status, notes. Chase missing rows.
- [ ] After every Kaggle submission, screenshot the submission history into `team-b/report/kaggle_evidence/`.
- [ ] `notebooks/results_charts.ipynb`: score-over-time line chart (Kaggle + dev) and per-variant bar chart vs base (G.4).

**V2 — Combined agent (draft Nov 20, dev Nov 21–22, slot Nov 23)**
- [ ] Pick every Team B variant that beat the base agent on dev (and did not raise avg time above ~5.5 min).
- [ ] Merge them into `team-b/combined/agent.yaml` one at a time; smoke after each addition to catch conflicts
      (e.g. critic + regression check may exceed the time budget).
- [ ] Optionally include Team A ideas that clearly worked (credit them in the README and report).
- [ ] Dev run, log, submit Nov 23.

**Phase 2 and report (Nov 24 – Dec 2)**
- [ ] Keep the Phase 2 slot bookings in the team chat; make sure every tuning run is logged.
- [ ] Nov 24: freeze; send Team B Kaggle evidence (team name, members, full history, baseline, best) to the report editor.
- [ ] Coordinate Phase 2 tuning slots; pick 2 finals by Dec 2 3:59 pm Pacific; final screenshots.
- [ ] Own report section: setup, baseline, patch hygiene, combined agent, score-over-time chart. Own slide.
- [ ] Review Parth's PRs.

---

### Parth — Multi-agent

**Setup (Nov 13–14)**
- [ ] Join competition, phone-verify Kaggle, install CLI, save token, accept Kaggle team + GitHub invites.
- [ ] Read `data/HARNESS_README.md` sections on `agent_tool` sub-agents and `agent.yaml`; read the sample
      `agent.yaml` line by line. Write 5 bullet notes in `team-b/docs/multi_agent_notes.md` on how sub-agents are
      declared, what they can return, and how much context they consume.
- [ ] Read [3] SWE-Protégé, [6] Category-aware experts, [11] Survey; note one sentence per paper for the report.

**V1 — Analyzer + coder (smoke by Nov 15, dev Nov 16, slot Nov 17)**
- [ ] The sample agent already includes an analyzer sub-agent (`sub_agents/code_analyzer.yaml`) that the main agent
      may call. Change **how it is used**: rewrite `prompts/analyzer.md` so it returns the 1–3 files to change and a
      short plan (files, functions, what to change) in ≤ 15 lines, and tell the main agent to call it first, every task.
- [ ] Main agent instructions: edit according to the analyzer's plan; read other files only if the plan is wrong.
- [ ] Watch time: the sub-agent costs turns. If smoke avg time > 5.5 min, cap the analyzer's turns in its instructions.
- [ ] Variant loop. README: What = analyzer sub-agent; Why = wrong-file failures; Source = [3], [11].
- [ ] Compare: wrong-file failures vs the base agent (use Naveen's labels).

**V2 — Coder + critic (smoke by Nov 18, dev Nov 19, slot Nov 20)**
- [ ] Copy the base agent again (not V1). Add a "critic" sub-agent that gets the issue + current diff and returns either
      "OK" or up to 3 concrete problems. Main agent calls it once before `submit_patch` and fixes listed problems.
- [ ] Variant loop. README: What = one critic round; Why = right-file-wrong-fix failures; Source = [3].
- [ ] Record how often the critic changed the patch and whether those tasks passed.

**Report (by Nov 22)**
- [ ] Report section: both designs, smoke/dev/Kaggle scores, what worked and what didn't, cost in time per task.
- [ ] One slide; contribution row. Review Ishan's PRs.

---

### Ishan — Retrieval / code graph, task EDA

**Setup (Nov 13–15)**
- [ ] Join competition, CLI, token, invites.
- [ ] **Task EDA (G.2) in Colab** (`team-b/notebooks/task_eda.ipynb`, CPU runtime) on `data/tasks.jsonl`:
      tasks per repo; issue text length; number of files and lines changed in the reference patch;
      share of single-file fixes; how often the changed file is named in the issue text.
      Write findings and 3–4 charts in `team-b/docs/task_eda.md`, each with "so we decided …"
      (e.g. "most fixes touch 1 file → analyzer returns ≤ 3 files").
- [ ] Learn the `graphs/` and `embeddings/` data formats and what `get_code_neighbors`, `search_similar_code`,
      `get_code_subgraph` return. Notes in `team-b/docs/retrieval_eval.md`.
- [ ] **Offline retrieval check (no GPU):** for each **train** task, take identifiers from the issue text, match them
      to files, and compute file-hit@1/@5 against the reference patch. Tune the matching on train only; report dev once.

**V1 — Graph-first localization (smoke by Nov 16, dev Nov 17, slot Nov 18)**
- [ ] Prompt/skill change: before reading files, pull identifiers (function, class, error names) from the issue,
      call `search_similar_code` with them, then `get_code_neighbors` on the top hit; read only the top 3 files.
- [ ] Variant loop. README: What = graph-first localization; Why = wrong-file + time spent searching; Source = [8], [7].
- [ ] Compare: tool calls before first edit vs the base agent (from traces).

**V2 — Graph expansion (smoke by Nov 19, dev Nov 20, slot Nov 21)**
- [ ] From the top matches, call `get_code_subgraph` to add callers, callees and related test files, capped at a fixed
      number of nodes so context stays small. Implement as a skill (`SKILL.md`) the agent loads.
- [ ] Variant loop. README: What = bounded graph expansion; Why = fixes that need a caller/callee change; Source = [8], [9].

**Report (by Nov 22)**
- [ ] Report section: EDA findings (G.2), retrieval hit rates, both variants, scores. One slide; contribution row.
- [ ] Review Naveen's PRs.

---

### Naveen — Testing & verification, error analysis

**Setup (Nov 13–15)**
- [ ] Join competition, CLI, token, invites.
- [ ] Get Team A's baseline error analysis (`docs/error_analysis.md`, Khushi) and failure labels:
      wrong file, right file wrong fix, broke other tests, timeout/looping, empty/invalid diff.
- [ ] Do **not** run the base yourself. Ask Dipin/Khushi for the base agent smoke/dev traces and Khushi's labels.
      Write `team-b/docs/error_analysis_b.md`: a short summary of the failure counts Team B targets (which member
      targets which type), then add labels for Team B variant runs as they come in.
- [ ] Read [3] SWE-Protégé, [4] SWE-Master, [12] SWE-bench.

**V1 — Reproduce-first skill (smoke Nov 14, dev Nov 14 overnight, slot Nov 15)**
- [ ] Add a skill folder `skills/reproduce-first/SKILL.md`: write a minimal script that shows the bug, run it and see
      it fail, fix the source, rerun until it passes, then delete the script before submitting.
- [ ] Variant loop. README: What = reproduce-first skill; Why = wrong-fix failures; Source = [3], [12].
- [ ] Check: no repro files left in patches (link with Ashmitha's hygiene numbers).

**V2 — Regression check (smoke by Nov 17, dev Nov 18, slot Nov 19)**
- [ ] Prompt/skill: before `submit_patch`, find the existing test file for each changed module and run only it
      (`pytest -q -x --tb=short <test_file>`); if a previously passing test fails, fix the source, not the test.
- [ ] Coordinate with Poushali (Team A, test-runner tool) so the two designs are different or clearly compared.
- [ ] Variant loop. README: What = targeted regression check; Why = broke-other-tests failures; Source = [4].

**Report (by Nov 22)**
- [ ] Report section: error analysis (G.2), both variants, scores, failure-type changes. One slide; contribution row.
- [ ] Write the "failed or ineffective approach" paragraph for whichever Team B variant did worst (G.3 requires one).
- [ ] Review Ashmitha's PRs.

## 8. Shared deliverables checklist (Team B side)

- [ ] Team B baseline submitted with screenshot (G.1, G.2)
- [ ] `competition_summary.md`, `task_eda.md`, `error_analysis_b.md` (G.1, G.2)
- [ ] 7 variants + combined, each with smoke + dev + Kaggle score in the log (G.3, G.4)
- [ ] ≥1 failed approach written up with what we learned (G.3)
- [ ] Score-over-time chart + full submission history screenshots (G.4, G.6)
- [ ] 4 report sections + 4 contribution rows + 4 slides to the group editors by Nov 22 (G.5)
- [ ] Peer review forms (all 4) after Dec 1

## 9. Risks

| Risk | What we do | Owner |
|---|---|---|
| Kaggle queue / runs slow | Start dev runs a day early with `--no-wait`; smoke first | Everyone |
| GPU quota runs out | Smoke before dev; swap a dev run to another member's quota | Ashmitha |
| Sub-agents push time over 6 min/task | Cap turns in instructions; check smoke avg time | Parth, Naveen |
| A variant misses its slot | Use spare (Nov 22/24/25); tell Ashmitha the day before | Everyone |
| Overlap with Team A | Areas chosen to differ; Naveen coordinates with Poushali | Ashmitha, Naveen |
| Overfitting to the 4 public repos | Never tune on dev; no repo-specific rules | Reviewers |
