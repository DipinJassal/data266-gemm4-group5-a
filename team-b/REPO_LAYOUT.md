# Team B — GitHub Repo Layout and Commit Plan

Repo: `DipinJassal/data266-gemm4-group5-a` (shared with Team A).
Team B works on the feature branch **`group5-team-b`**, inside a `team-b/` folder, so Team A's `main` is never touched
and both teams use the same `harness/` and task lists.

> Git branch names cannot contain spaces, so "group 5 team b" becomes `group5-team-b`.
> Because a branch named `group5-team-b` exists, Git cannot also create branches named `group5-team-b/<something>`
> (the names would clash). Personal branches therefore use the prefix `b/`.

Fallback if Team B does not get write access: fork the repo to Ashmitha's account and use the same branch and layout there.

## 1. Branch model

```
main                         Team A (never push here)
└── group5-team-b            Team B integration branch (all Team B PRs merge here)
    ├── b/setup              Ashmitha: workspace, experiment log, competition summary
    ├── b/baseline           Ashmitha: base agent
    ├── b/patch-hygiene      Ashmitha: V1
    ├── b/combined           Ashmitha: V2 (combined agent)
    ├── b/analyzer-plan      Parth: V1
    ├── b/diff-critic        Parth: V2
    ├── b/task-eda           Ishan: task EDA (G.2)
    ├── b/graph-localize     Ishan: V1
    ├── b/graph-expand       Ishan: V2
    ├── b/error-analysis     Naveen: error analysis (G.2)
    ├── b/repro-first        Naveen: V1
    └── b/regression-check   Naveen: V2
```

- One short branch per task, PR into `group5-team-b`, reviewer approves, squash-merge, delete the branch.
- Pull Team A's harness fixes into Team B regularly: `git checkout group5-team-b && git merge origin/main`.
- Each member only edits their own folders, so merge conflicts are rare. Only Ashmitha edits
  `team-b/TEAM_B_GUIDE.md`, `team-b/README.md` and `team-b/combined/`; everyone appends rows to `experiment_log.csv`.

## 2. Folder layout (on `group5-team-b`)

```
data266-gemm4-group5-a/
├── README.md                       Team A root files (unchanged)
├── baseline/                       Unmodified sample agent (shared, never edit)
├── harness/                        Team A's harness + splits (shared, never edit; ask Dipin)
│   ├── splits/{smoke,dev,train}.txt
│   ├── validate.py  run_kaggle.py  kaggle_runner.py  summarize.py
│   └── runs/                       Downloaded results (git-ignored)
├── variants/                       Team A variants (never edit)
├── data/                           Competition data (git-ignored)
└── team-b/
    ├── TEAM_B_GUIDE.md             Team B rules, roles, status, calendar (Ashmitha)
    ├── README.md                   Overview + run commands (Ashmitha)
    ├── TEAM_B_PLAN.md              Detailed plan and per-member to-dos (Ashmitha)
    ├── REPO_LAYOUT.md              This file (Ashmitha)
    ├── docs/
    │   ├── competition_summary.md  Lead & evaluation (G.1): Ashmitha
    │   ├── task_eda.md             Retrieval (G.2): Ishan
    │   ├── retrieval_eval.md       Retrieval: Ishan
    │   ├── multi_agent_notes.md    Multi-agent: Parth
    │   ├── error_analysis_b.md     Verification (G.2): Naveen
    │   └── experiment_log.csv      Everyone appends; Ashmitha keeps it complete
    ├── notebooks/
    │   ├── task_eda.ipynb          Retrieval (Colab, CPU): Ishan
    │   ├── retrieval_eval.ipynb    Retrieval (Colab, CPU): Ishan
    │   └── results_charts.ipynb    Lead & evaluation, score over time (G.4): Ashmitha
    ├── variants/
    │   ├── _template/README.md     3-line README template
    │   ├── base/                   Starting point for every variant (not a variant)
    │   ├── patch-hygiene/          V1 Lead & evaluation: Ashmitha
    │   ├── analyzer-plan/          V1 Multi-agent: Parth
    │   ├── diff-critic/            V2 Multi-agent: Parth
    │   ├── graph-localize/         V1 Retrieval: Ishan
    │   ├── graph-expand/           V2 Retrieval: Ishan (+ skills/graph-expand/SKILL.md)
    │   ├── repro-first/            V1 Verification: Naveen (+ skills/reproduce-first/SKILL.md)
    │   └── regression-check/       V2 Verification: Naveen
    ├── combined/                   V2 Lead & evaluation, combined agent: Ashmitha
    ├── results/                    Small run summaries from summarize.py (each owner commits theirs)
    ├── report/
    │   ├── sections/
    │   │   ├── lead-evaluation.md  Ashmitha
    │   │   ├── multi-agent.md      Parth
    │   │   ├── retrieval.md        Ishan
    │   │   └── verification.md     Naveen
    │   ├── contribution_table.md   Everyone adds their row; Ashmitha compiles
    │   └── kaggle_evidence/        Submission history screenshots: Ashmitha
    └── slides/
        ├── lead-evaluation.md      Ashmitha
        ├── multi-agent.md          Parth
        ├── retrieval.md            Ishan
        └── verification.md         Naveen
```

Variant folder names have **no version suffix** (V1/V2 is tracked in `TEAM_B_GUIDE.md`, "Variants and folders").
Add `-2`, `-3` only when the same idea is revised, e.g. `diff-critic-2`. Names must stay **19 characters or less** (e.g. `analyzer-plan`). The harness builds the
Kaggle kernel name as `g5a-eval-<path>-<split>` cut to 50 characters; with the `team-b/variants/` prefix, longer
names lose the `-smoke`/`-dev` ending, so smoke and dev runs overwrite each other.

Do not commit: `data/`, `harness/runs/`, `submission.zip`, `~/.kaggle/` tokens, large logs. Commit only small summaries.

## 3. One-time setup (Ashmitha)

```bash
git clone https://github.com/DipinJassal/data266-gemm4-group5-a.git
```

```bash
cd data266-gemm4-group5-a && git checkout -b group5-team-b
```

```bash
mkdir -p team-b/{docs,notebooks,variants/_template,combined,results,report/sections,report/kaggle_evidence,slides}
```

Copy `TEAM_B_GUIDE.md`, `TEAM_B_PLAN.md`, `REPO_LAYOUT.md` into `team-b/`, then:

```bash
git add team-b && git commit -m "chore(team-b): add Team B skeleton, guide, plan and layout" && git push -u origin group5-team-b
```

Other members:

```bash
git fetch origin && git checkout group5-team-b
```

## 4. Commit plan (in order, by date)

Messages use the `type(scope): summary` style. Each block is one branch → one PR into `group5-team-b`.

### Nov 13 — Setup and baseline
| Branch | Who | Commits |
|---|---|---|
| `group5-team-b` (direct, first commit only) | Ashmitha | `chore(team-b): add Team B skeleton, guide, plan and layout` |
| `b/setup` | Ashmitha | `docs(team-b): add experiment log with shared columns`<br>`docs(team-b): add variant README template`<br>`docs(team-b): add competition summary (task, metric, rules, limits)` |
| `b/baseline` | Ashmitha | `docs(team-b): log baseline Kaggle submission and score`<br>`docs(team-b): add baseline submission screenshot` |

### Nov 14 — Base v0, EDA, error analysis
| Branch | Who | Commits |
|---|---|---|
| `b/baseline` (cont.) | Ashmitha | `feat(team-b): add budget-fixed base agent (copy of dipin-step-budget-v1)`<br>`docs(team-b): record base agent scores from Team A's runs` |
| `b/task-eda` | Ishan | `feat(team-b): add task EDA notebook`<br>`docs(team-b): add task EDA findings and charts` |
| `b/error-analysis` | Naveen | `docs(team-b): summarize Team A failure counts and Team B targets` |

### Nov 14–15 — Naveen V1
| `b/repro-first` | Naveen | `feat(team-b): add repro-first variant folder`<br>`feat(team-b): add reproduce-first skill`<br>`docs(team-b): log repro-first smoke and dev results` |
|---|---|---|

### Nov 15–16 — Ashmitha V1
| `b/patch-hygiene` | Ashmitha | `feat(team-b): add patch-hygiene variant folder`<br>`feat(team-b): add pre-submit checklist to system prompt`<br>`docs(team-b): log patch-hygiene results and empty-patch counts` |
|---|---|---|

### Nov 14–17 — Parth V1
| `b/analyzer-plan` | Parth | `docs(team-b): add multi-agent notes from harness docs`<br>`feat(team-b): add analyzer-plan variant folder`<br>`feat(team-b): add analyzer sub-agent and call it first`<br>`fix(team-b): cap analyzer turns to stay under time budget` (if needed)<br>`docs(team-b): log analyzer-coder results` |
|---|---|---|

### Nov 14–18 — Ishan V1
| `b/graph-localize` | Ishan | `feat(team-b): add offline retrieval eval notebook`<br>`docs(team-b): add file-hit@k results on train`<br>`feat(team-b): add graph-localize variant folder`<br>`feat(team-b): add graph-first localization instructions`<br>`docs(team-b): log graph-localize results` |
|---|---|---|

### Nov 17–19 — Naveen V2
| `b/regression-check` | Naveen | `feat(team-b): add regression-check variant folder`<br>`feat(team-b): run related tests before submit`<br>`docs(team-b): log regression-check results` |
|---|---|---|

### Nov 18–20 — Parth V2
| `b/diff-critic` | Parth | `feat(team-b): add diff-critic variant folder`<br>`feat(team-b): add critic sub-agent with one review round`<br>`docs(team-b): log coder-critic results and critic change rate` |
|---|---|---|

### Nov 19–21 — Ishan V2
| `b/graph-expand` | Ishan | `feat(team-b): add graph-expand variant folder`<br>`feat(team-b): add bounded graph-expansion skill`<br>`docs(team-b): log graph-expand results` |
|---|---|---|

### Nov 20–23 — Combined agent
| `b/combined` | Ashmitha | `feat(team-b): start combined agent from the base agent`<br>`feat(team-b): merge <variant> into combined agent` (one commit per merged variant)<br>`docs(team-b): log combined smoke and dev results`<br>`docs(team-b): add score-over-time chart` |
|---|---|---|

### Nov 22 — Report and slides (each member, own branch `b/report-<area>`)
`docs(team-b): add <area> report section`<br>`docs(team-b): add <area> slide notes`<br>`docs(team-b): add <area> contribution row`

### Nov 24 – Dec 2 — Freeze and Phase 2
| Branch | Who | Commits |
|---|---|---|
| `b/kaggle-evidence` | Ashmitha | `docs(team-b): add Kaggle submission history screenshots (freeze)` |
| `b/tune-<what>` | Anyone | `feat(team-b): tune <setting> in combined agent`<br>`docs(team-b): log tuning run` |
| `b/final-picks` | Ashmitha | `docs(team-b): record 2 final submissions and final standing` |

## 5. PR checklist (paste into every PR description)

```
- [ ] Changes exactly one thing from base (or: combined agent)
- [ ] 3-line README filled in (What changed / Why / Source)
- [ ] validate.py passes; zip has agent.yaml at the root; only allowed tools
- [ ] Smoke ran with no crashes; avg time per task < 6 min
- [ ] Dev score logged in team-b/docs/experiment_log.csv next to the base agent
- [ ] No repo-specific logic; nothing tuned on dev tasks (one dev run, after the variant was final)
- [ ] Reviewer tagged (rotation: Ashmitha → Parth → Ishan → Naveen → Ashmitha)
```
