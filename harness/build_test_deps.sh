#!/usr/bin/env bash
# Build (or rebuild) the private Kaggle dataset used by `run_kaggle.py --test-deps`.
# Downloads Linux / CPython 3.12 wheels (the pinned Kaggle image runs Python 3.12.13, pytest 8.4.2) for the test-only
# packages the competition wheels lack, plus their dependencies, into a flat folder with a marker file.
#
#   bash harness/build_test_deps.sh <out_dir>            # download only
#   kaggle datasets create -p <out_dir>                   # first upload (private)
#   kaggle datasets version -p <out_dir> -m "rebuild"     # later uploads
#
# Pins follow the repos: fastapi requirements-tests.txt / pyproject (dirty-equals ==0.9.0, inline-snapshot >=0.21.1),
# requests requirements-dev.txt (pytest-httpbin ==2.1.0, httpbin ~=0.10.0). pytest is pinned to the sandbox's 8.4.2 so
# the resolver picks plugin versions that work with it. Keep in sync with TEST_DEPS in harness/kaggle_runner.py.
set -euo pipefail
out="${1:?usage: build_test_deps.sh <out_dir>}"
mkdir -p "$out"
python3 -m pip download -q -d "$out" --only-binary=:all: \
  --python-version 3.12 --implementation cp --abi cp312 \
  --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_28_x86_64 --platform any \
  "dirty-equals==0.9.0" "inline-snapshot>=0.21.1,<0.32" "pytest-httpbin==2.1.0" "httpbin~=0.10.0" "pytest==8.4.2"
echo "g5a test-deps wheels for kaggle_runner.install_test_deps (built $(date -u +%Y-%m-%dT%H:%MZ))" > "$out/G5A_TEST_DEPS_MARKER"
cat > "$out/dataset-metadata.json" <<'EOF'
{"title": "g5a-test-deps", "id": "dipinjassal/g5a-test-deps", "isPrivate": true, "licenses": [{"name": "other"}]}
EOF
ls "$out"
