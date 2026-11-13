# Team B (GROUP_PROGRAMMING_05_b) — Gemma 4 Developer Agent

Team B is the 4-member Kaggle team of DATA 266 Group 5 (Ashmitha, Parth, Ishan, Naveen).
Team A (5 members) works on `main`; Team B works on the `group5-team-b` branch inside this `team-b/` folder.
Both teams share the harness, task splits, report and presentation.

Read [TEAM_B_GUIDE.md](TEAM_B_GUIDE.md) first, then [TEAM_B_PLAN.md](TEAM_B_PLAN.md) for your tasks and
[REPO_LAYOUT.md](REPO_LAYOUT.md) for branches and commits.

## Make a variant

```bash
git checkout group5-team-b && git pull
git checkout -b b/<variant>
cp -r team-b/variants/base team-b/variants/<short>   # name <= 19 characters
cp team-b/variants/_template/README.md team-b/variants/<short>/README.md
# make ONE change, fill in the 3-line README
python harness/validate.py team-b/variants/<short> --zip submission.zip
python harness/run_kaggle.py team-b/variants/<short> smoke --max-tasks 2
```

Then smoke (10 tasks), dev (30 tasks, once the variant is final; see "Evaluation splits" in `TEAM_B_GUIDE.md`), log the row in `docs/experiment_log.csv`, open a PR into
`group5-team-b` and tag your reviewer (Ashmitha → Parth → Ishan → Naveen → Ashmitha).
