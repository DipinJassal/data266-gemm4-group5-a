# Run guide (Sarvesh)

How to run the sample agent, build `submission.zip`, and submit.
Scored runs need a Kaggle **L4×4** GPU; offline validate/zip works on any laptop.

Competition: [Gemma 4 Developer Agent](https://www.kaggle.com/competitions/gemma-4-developer-agent).
Official notebook: `ryanholbrook/getting-started-gemma-4-developer-agent`.
Team harness details: `harness/README.md`.

## 0. One-time setup (every machine)

1. Accept the competition rules on Kaggle.
2. Install the Kaggle CLI and save your API token:
   ```bash
   pip install kaggle
   # put access_token (or kaggle.json) in ~/.kaggle/
   ```
3. Clone this repo and download competition files (git-ignored under `data/`):
   ```bash
   kaggle competitions download gemma-4-developer-agent -f tasks.jsonl -p data
   kaggle competitions download gemma-4-developer-agent -f HARNESS_README.md -p data
   ```
4. **Adapter weights:** `.gitignore` excludes `*.safetensors`, so a fresh clone of `baseline/` is missing
   `adapters/*/adapter_model.safetensors`. Download Kaggle's `sample_submission` adapters into those folders
   before `validate.py` / `run_kaggle.py` will pass. (Dummy zero-init weights; required for the zip layout.)

## 1. Run a few tasks (recommended: team harness)

From the repo root, on your laptop (uses **your** Kaggle GPU quota):

```bash
# Quick end-to-end check (2 tasks)
python harness/run_kaggle.py baseline smoke --max-tasks 2

# Full smoke (10 tasks) — crash / timing check
python harness/run_kaggle.py baseline smoke

# Dev score (30 tasks) — the number we log next to the baseline
python harness/run_kaggle.py baseline dev
```

What happens: offline validate → upload agents as a private dataset → push a GPU kernel → wait → download
results into `harness/runs/baseline/<split>/<UTC stamp>/`.

Expect ~10–20 min of vLLM start-up per kernel (plus Kaggle queue time). Per-task wall time is realistic;
startup does not count toward the per-task budget.

Useful flags:

```bash
python harness/run_kaggle.py baseline smoke --task-ids rich_3180   # one task
python harness/run_kaggle.py baseline smoke --no-wait              # push and leave
python harness/run_kaggle.py --fetch baseline smoke                # download later
python harness/run_kaggle.py baseline smoke --dry-run              # no Kaggle calls
```

Summarize and compare:

```bash
python harness/summarize.py harness/runs/baseline/dev/<stamp> --csv
python harness/summarize.py harness/runs/<variant>/dev/<stamp> \
  --baseline harness/runs/baseline/dev/<stamp> --csv
```

### Alternative: official Getting Started notebook

1. Open `ryanholbrook/getting-started-gemma-4-developer-agent` on Kaggle.
2. Copy / attach the sample submission (or our `baseline/` as a dataset).
3. Run a small task list there. Prefer the harness above for scores that match the team log
   (same splits, same summary format).

## 2. Build `submission.zip`

A competition submission is a zip with **`agent.yaml` at the root** (declarative YAML only).

```bash
# Checks only (no GPU)
python harness/validate.py baseline

# Build the zip we upload to Kaggle
python harness/validate.py baseline --zip submission.zip
```

Same pattern for any variant:

```bash
python harness/validate.py variants/<owner>-<name>-v1 --zip submission.zip
```

Checks include: root `agent.yaml`, allowed extensions, no symlinks, size &lt; 3 GiB, `!include` stays inside
the folder, team model only, harness tools only, adapters present, token limits ≤ 32,768.

Confirm the zip layout:

```bash
# PowerShell
Add-Type -AssemblyName System.IO.Compression.FileSystem
[IO.Compression.ZipFile]::OpenRead("$PWD\submission.zip").Entries |
  Select-Object -ExpandProperty FullName | Select-Object -First 20
```

You should see `agent.yaml` (and the rest of the agent tree) at the **root of the zip**, not nested under
an extra folder.

## 3. Submit on Kaggle

1. Only submit through the **team** Kaggle account, on your calendar date (see `CLAUDE.md`).
2. Competition → Submit Prediction → upload `submission.zip`.
3. **1 submission per team per day** (day resets 4:00 pm Pacific / 00:00 UTC).
4. After scoring, download the run outputs (or keep the harness `harness/runs/...` folder) and:
   - log the row in the team experiment log (`docs/experiment_log.xlsx`);
   - share the run ZIP / logs with whoever needs them (Khushi for baseline error analysis).

### Baseline (unmodified sample) — Nov 10 slot

- Folder: `baseline/` (never edit; byte-identical to Kaggle `sample_submission/`).
- Build: `python harness/validate.py baseline --zip submission.zip`
- Submit that zip unchanged on the team's Nov 10 slot (or confirm Dipin's harness `baseline` / `dev`
  run is recorded as the team's baseline if the calendar slot was already used for the harness score).
- Known harness score (Nov 10, Dipin): **2/30 = 6.7%** on `dev`. Details: `docs/baseline_profile.md`
  and Khushi's `docs/error_analysis.md` (branch `khushi/experiment-log` until merged).

## 4. Budget warning (read before interpreting scores)

The sample `baseline/eval_config.yaml` caps each task at:

- `max_time_minutes: 1`
- `max_tool_calls: 10`

Most tasks time out before an edit. That is expected for the unmodified baseline — submit it anyway,
and treat Dipin's budget-fixed V2 (`variants/dipin-step-budget-v1`, 4.5 min / 50 calls) as the control
for later variants (team proposal; see `CLAUDE.md`).
