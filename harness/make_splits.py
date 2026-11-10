"""Build the task splits from the competition's tasks.jsonl.

    python harness/make_splits.py data/tasks.jsonl

Writes harness/splits/{dev,train,smoke}.txt (one instance_id per line, sorted).

- dev   (30): stratified by repo, so all 4 public repos are present. Scoring only; never train or tune on it.
- train (99): every task not in dev. LoRA training data.
- smoke (10): a stratified subset of TRAIN, for crash/runtime checks and quick sweeps.
  It is taken from train (not dev) so that tuning on smoke never leaks into the dev score.

The split is deterministic (fixed seed), so re-running it gives the same files.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

SEED = 266
DEV_SIZE = 30
SMOKE_SIZE = 10
SPLITS_DIR = Path(__file__).resolve().parent / "splits"


def stratified_sample(ids_by_repo: dict[str, list[str]], n: int, rng: random.Random) -> list[str]:
    """Sample n ids, proportional to repo size, with at least one id from every repo."""
    total = sum(len(v) for v in ids_by_repo.values())
    repos = sorted(ids_by_repo)
    quota = {r: max(1, round(n * len(ids_by_repo[r]) / total)) for r in repos}
    # Fix rounding drift by adjusting the largest repos first.
    by_size = sorted(repos, key=lambda r: -len(ids_by_repo[r]))
    i = 0
    while sum(quota.values()) != n:
        r = by_size[i % len(by_size)]
        if sum(quota.values()) > n and quota[r] > 1:
            quota[r] -= 1
        elif sum(quota.values()) < n and quota[r] < len(ids_by_repo[r]):
            quota[r] += 1
        i += 1
    picked: list[str] = []
    for r in repos:
        picked += rng.sample(sorted(ids_by_repo[r]), quota[r])
    return sorted(picked)


def group(ids: list[str], repo_of: dict[str, str]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for i in ids:
        out[repo_of[i]].append(i)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("tasks", type=Path, help="path to tasks.jsonl")
    args = ap.parse_args()

    repo_of = {}
    for line in args.tasks.read_text().splitlines():
        if line.strip():
            t = json.loads(line)
            repo_of[t["instance_id"]] = t["repo"]
    all_ids = sorted(repo_of)

    rng = random.Random(SEED)
    dev = stratified_sample(group(all_ids, repo_of), DEV_SIZE, rng)
    train = sorted(set(all_ids) - set(dev))
    smoke = stratified_sample(group(train, repo_of), SMOKE_SIZE, rng)

    assert not set(dev) & set(train), "dev and train overlap"
    assert set(smoke) <= set(train), "smoke must be a subset of train"
    assert len(set(repo_of[i] for i in dev)) == len(set(repo_of.values())), "dev must cover every repo"

    SPLITS_DIR.mkdir(exist_ok=True)
    for name, ids in (("dev", dev), ("train", train), ("smoke", smoke)):
        (SPLITS_DIR / f"{name}.txt").write_text("\n".join(ids) + "\n")
        counts = defaultdict(int)
        for i in ids:
            counts[repo_of[i]] += 1
        print(f"{name:5s} {len(ids):3d}  " + ", ".join(f"{r}={c}" for r, c in sorted(counts.items())))


if __name__ == "__main__":
    main()
