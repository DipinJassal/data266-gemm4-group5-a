"""Team B wrapper around the shared harness/run_kaggle.py (the harness itself is not modified).

The shared launcher uploads only baseline/, variants/, combined/ and harness/ to the private Kaggle
dataset, so a team-b/variants/<name> run fails inside the kernel with "No agent.yaml". This wrapper
adds team-b/ to the upload, normalizes Windows paths, and then runs the shared launcher unchanged.

    python team-b/tools/run_kaggle_b.py team-b/variants/<name> smoke --max-tasks 2
    python team-b/tools/run_kaggle_b.py team-b/variants/<name> dev --no-wait
    python team-b/tools/run_kaggle_b.py --fetch team-b/variants/<name> dev
"""

import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[2] / "harness"
sys.path.insert(0, str(HARNESS))

import run_kaggle  # noqa: E402

if "team-b" not in run_kaggle.UPLOAD_DIRS:
    run_kaggle.UPLOAD_DIRS = (*run_kaggle.UPLOAD_DIRS, "team-b")
# Kaggle runs Linux: pass posix paths in RUN_CONFIG (same fix as main's harness).
sys.argv = [a.replace("\\", "/") if "variants" in a else a for a in sys.argv]

if __name__ == "__main__":
    sys.exit(run_kaggle.main())
