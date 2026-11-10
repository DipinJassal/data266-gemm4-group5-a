"""Summarize a harness run (and optionally compare it with the baseline run on the same split).

    python harness/summarize.py harness/runs/baseline/smoke/<stamp>/.../results/baseline/smoke
    python harness/summarize.py <run_dir> --baseline <baseline_run_dir>
    python harness/summarize.py <run_dir> --csv          # also print a row for the team experiment log

<run_dir> is any folder containing harness_results.jsonl (searched recursively), as written by kaggle_runner.py.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

TARGET_MINUTES = 6.0


def load(run_dir: Path) -> tuple[list[dict], dict]:
    path = run_dir if run_dir.name == "harness_results.jsonl" else next(run_dir.rglob("harness_results.jsonl"), None)
    if path is None:
        raise SystemExit(f"no harness_results.jsonl under {run_dir}")
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    info_path = path.parent / "run_info.json"
    info = json.loads(info_path.read_text()) if info_path.exists() else {}
    return rows, info


def minutes(r: dict) -> float:
    secs = r.get("wall_seconds") or r.get("duration_seconds") or 0
    return float(secs) / 60


def outcome(r: dict) -> str:
    if r.get("resolved"):
        return "PASS"
    err = str(r.get("error") or "")
    if err.startswith("HARNESS_CRASH"):
        return "CRASH"
    if not r.get("patch_chars"):
        return "EMPTY"
    return "FAIL"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--baseline", type=Path, help="baseline run on the same split, for a side-by-side comparison")
    ap.add_argument("--csv", action="store_true", help="print a row for the team experiment log")
    args = ap.parse_args()

    rows, info = load(args.run_dir)
    base = {}
    if args.baseline:
        base_rows, _ = load(args.baseline)
        base = {r["instance_id"]: r for r in base_rows}

    n = len(rows)
    resolved = sum(bool(r.get("resolved")) for r in rows)
    times = [minutes(r) for r in rows]
    avg_t = sum(times) / n if n else 0.0

    print(f"\nVariant: {info.get('variant', '?')}   split: {info.get('split', '?')}   model: {info.get('model', '?')}   "
          f"git: {info.get('git_rev', '?')}")
    if info.get("budgets"):
        b = info["budgets"]
        print(f"Budget per task: {b.get('max_time_minutes')} min, {b.get('max_tool_calls')} tool calls, {b.get('max_turns')} turns   "
              f"GPUs: {info.get('gpu_count')}")
    print()
    header = f"{'task':22s} {'result':6s} {'min':>5s} {'tools':>5s} {'patch':>6s}"
    if base:
        header += "  baseline"
    print(header)
    print("-" * len(header))
    for r in rows:
        line = (f"{r['instance_id']:22s} {outcome(r):6s} {minutes(r):5.1f} {str(r.get('tool_calls', '-')):>5s} "
                f"{r.get('patch_chars', 0):>6d}")
        if base:
            b = base.get(r["instance_id"])
            line += f"  {outcome(b) if b else '-':6s}"
            if b and bool(b.get('resolved')) != bool(r.get('resolved')):
                line += "  <- gained" if r.get("resolved") else "  <- lost"
        print(line)

    print()
    by_repo = defaultdict(lambda: [0, 0])
    for r in rows:
        by_repo[r["repo"]][0] += bool(r.get("resolved"))
        by_repo[r["repo"]][1] += 1
    counts = defaultdict(int)
    for r in rows:
        counts[outcome(r)] += 1

    print(f"Resolved: {resolved}/{n} = {100 * resolved / n:.1f}%" if n else "Resolved: 0/0")
    if base:
        common = [r for r in rows if r["instance_id"] in base]
        b_res = sum(bool(base[r["instance_id"]].get("resolved")) for r in common)
        v_res = sum(bool(r.get("resolved")) for r in common)
        print(f"Baseline on the same {len(common)} tasks: {b_res}   (variant {v_res}, delta {v_res - b_res:+d})")
    print("Per repo: " + ", ".join(f"{k.split('/')[-1]} {v[0]}/{v[1]}" for k, v in sorted(by_repo.items())))
    print("Outcomes: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"Time per task: avg {avg_t:.1f} min, max {max(times, default=0):.1f} min "
          f"({'OK' if avg_t <= TARGET_MINUTES else 'OVER'} vs ~{TARGET_MINUTES:.0f} min target)")

    if args.csv:
        split = info.get("split", "?")
        smoke_time = f"{avg_t:.1f}" if split == "smoke" else ""
        dev_score = f"{100 * resolved / n:.1f}%" if split == "dev" and n else ""
        print("\nvariant,owner,one-line change,smoke time,dev score,Kaggle score,status,notes")
        print(f"{info.get('variant', '?')},,,{smoke_time},{dev_score},,,"
              f"{resolved}/{n} on {split} @ {info.get('git_rev', '?')}")


if __name__ == "__main__":
    main()
