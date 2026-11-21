"""V2 data (Bhoomika): turn successful agent runs into LoRA training examples, filtered by error-retry rate.

    python lora/v2/curate.py --train <run dir> [<run dir> ...] --heldout <run dir> [...] --out <dir>

A run dir is a fetched harness run (harness/runs/<variant>/<split>/<stamp>): it holds results/*/<split>/harness_results.jsonl
and swegemma/traces/trace_<id>.json. Only resolved tasks are used. Training tasks must be in train.txt and not in smoke.txt
or dev.txt; held-out tasks must be in smoke.txt (held-out loss only). Dev tasks are never read.

Each trace becomes one chat: the harness's system prompt and task prompt, then for every agent step an assistant message
(the model's thought as `reasoning`, its tool call) and the tool's response, then the final answer. Unlike V1, the model's
own thinking and its recoveries from failed calls are kept, so the adapter does not learn to skip thinking.

Filter ([10] Han: the error-retry rate is the best single quality signal): drop a run if more than MAX_ERR_RATE of its
tool calls failed, or if it repeated the same failing call MAX_REPEAT times. Runs with harness interruptions
(context-window errors, continuation nudges) are dropped too, since the served model never sees those as normal turns.
"""

import argparse
import glob
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SPLITS = REPO / "harness" / "splits"
MAX_ERR_RATE = 0.25
MAX_REPEAT = 3


def ids(name):
    return {l.strip() for l in (SPLITS / f"{name}.txt").read_text().splitlines() if l.strip()}


def failed(tool, content):
    try:
        o = json.loads(content)
    except (TypeError, ValueError):
        return False
    if not isinstance(o, dict):
        return False
    if o.get("status") not in (None, "ok"):
        return True
    # grep with no match exits 1: not an error the agent has to recover from
    return tool == "run_command" and o.get("exit_code") not in (None, 0, 1)


def to_chat(trace):
    steps = trace["steps"]
    if steps[0]["source"] != "system" or steps[1]["source"] != "user":
        return None, "unexpected start"
    msgs = [{"role": "system", "content": steps[0]["message"]}, {"role": "user", "content": steps[1]["message"]}]
    pending_thought, calls, fails, final = None, [], [], None
    for s in steps[2:]:
        if s["source"] != "agent":
            return None, f"harness step: {s.get('extra', {}).get('event_type') or 'error'}"
        et = s.get("extra", {}).get("event_type")
        tcs = s.get("tool_calls") or []
        if et == "final":
            final = s.get("message") or ""
            continue
        if not tcs:
            # a thought with no call: it belongs to the next call or to the final answer
            pending_thought = "\n\n".join(x for x in (pending_thought, s.get("message")) if x)
            continue
        if len(tcs) != 1 or "observation" not in s:
            return None, "parallel calls"
        tc = tcs[0]
        thought = "\n\n".join(x for x in (pending_thought, s.get("message")) if x) or None
        pending_thought = None
        cid = tc["tool_call_id"]
        a = {"role": "assistant", "content": "", "tool_calls": [{"id": cid, "type": "function", "function": {
            "name": tc["function_name"], "arguments": tc.get("arguments") or {}}}]}
        if thought:
            a["reasoning"] = thought
        content = s["observation"].get("content", "")
        msgs += [a, {"role": "tool", "tool_call_id": cid, "name": tc["function_name"], "content": content}]
        calls.append((tc["function_name"], json.dumps(tc.get("arguments") or {}, sort_keys=True)))
        fails.append(failed(tc["function_name"], content))
    if not calls:
        return None, "no tool calls"
    if final is not None or pending_thought:
        m = {"role": "assistant", "content": final or ""}
        if pending_thought:
            m["reasoning"] = pending_thought
        msgs.append(m)
    err_rate = sum(fails) / len(calls)
    worst_repeat = max(Counter(c for c, f in zip(calls, fails) if f).values(), default=0)
    stats = {"tool_calls": len(calls), "failed_calls": sum(fails), "err_rate": round(err_rate, 3), "worst_repeat": worst_repeat}
    if err_rate > MAX_ERR_RATE:
        return stats, f"error-retry rate {err_rate:.2f}"
    if worst_repeat >= MAX_REPEAT:
        return stats, f"same failing call x{worst_repeat}"
    return (msgs, stats), None


CHAR_BUDGET = 34000   # ~9.2K tokens at ~3.7 chars/token (measured in the dry run) for code + JSON; the trainer drops anything still too long
OLD_OBS_CHARS = 300   # older tool responses are cut to this, like the harness's summarizing of older turns


def size(m):
    return len(m.get("content") or "") + len(m.get("reasoning") or "") + len(json.dumps(m.get("tool_calls") or ""))


def split_windows(ex):
    """Split one long run into pieces that fit the trainer. Each piece keeps the system + task prompt and all earlier
    calls (older thoughts dropped, older tool responses cut to OLD_OBS_CHARS) and trains only on a window of
    consecutive steps, given as call indexes [a, b) plus whether the final answer is in it."""
    msgs = ex["messages"]
    head, rest = msgs[:2], msgs[2:]
    turns, i = [], 0                      # turn = assistant call + its tool response, or the final answer
    while i < len(rest):
        if rest[i].get("tool_calls"):
            turns.append(rest[i:i + 2]); i += 2
        else:
            turns.append(rest[i:i + 1]); i += 1
    has_final = not turns[-1][0].get("tool_calls")
    n_calls = len(turns) - has_final
    fixed = sum(size(m) for m in head) + len(json.dumps(ex["tools"]))

    def short(t):
        out = []
        for m in t:
            m = dict(m)
            m.pop("reasoning", None)
            if m["role"] == "tool" and len(m["content"]) > OLD_OBS_CHARS:
                m["content"] = m["content"][:OLD_OBS_CHARS] + " ...[older output trimmed]"
            out.append(m)
        return out

    pieces, a = [], 0
    while a < len(turns):
        old = [m for t in turns[:a] for m in short(t)]
        used = fixed + sum(size(m) for m in old)
        b = a
        while b < len(turns) and (b == a or used + sum(size(m) for m in turns[b]) <= CHAR_BUDGET):
            used += sum(size(m) for m in turns[b]); b += 1
        win = [m for t in turns[a:b] for m in t]
        pieces.append({**{k: v for k, v in ex.items() if k != "messages"}, "piece": f"{len(pieces) + 1}",
                       "messages": head + old + win, "loss_calls": [a, min(b, n_calls)],
                       "loss_final": has_final and b == len(turns), "est_chars": used})
        a = b
    for p in pieces:
        p["piece"] = f"{p['piece']}/{len(pieces)}"
    return pieces


def collect(run_dirs, allowed, tools):
    out, report = {}, []
    for rd in run_dirs:
        for res in glob.glob(str(Path(rd) / "results" / "*" / "*" / "harness_results.jsonl")):
            res = Path(res)
            for line in res.read_text(encoding="utf-8").splitlines():
                r = json.loads(line)
                iid = r["instance_id"]
                row = {"run": str(Path(rd).relative_to(REPO)) if Path(rd).is_relative_to(REPO) else str(rd), "id": iid,
                       "resolved": r["resolved"]}
                if iid not in allowed:
                    row["skip"] = "not in allowed split"
                elif not r["resolved"]:
                    row["skip"] = "not resolved"
                elif iid in out:
                    row["skip"] = "duplicate (kept first run)"
                else:
                    tr = res.parent / "swegemma" / "traces" / f"trace_{iid}.json"
                    if not tr.exists():
                        row["skip"] = "no trace"
                    else:
                        got, why = to_chat(json.loads(tr.read_text(encoding="utf-8")))
                        if why:
                            row["skip"] = why
                            if isinstance(got, dict):
                                row.update(got)
                        else:
                            msgs, stats = got
                            row.update(stats)
                            out[iid] = {"instance_id": iid, "messages": msgs, "tools": tools, **stats}
                report.append(row)
    return list(out.values()), report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", nargs="+", required=True)
    ap.add_argument("--heldout", nargs="*", default=[])
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tools = json.loads((Path(__file__).parent / "tools.json").read_text(encoding="utf-8"))
    dev, smoke, train = ids("dev"), ids("smoke"), ids("train")
    assert not dev & train
    tr, rep_tr = collect(a.train, train - smoke, tools)
    ho, rep_ho = collect(a.heldout, smoke, tools)
    assert not {x["instance_id"] for x in tr + ho} & dev
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("v2_train", tr), ("v2_heldout", ho)):
        rows = [p for x in rows for p in split_windows(x)]
        print(f"{name}: {len(rows)} pieces, est chars {sorted(p['est_chars'] for p in rows)}")
        (out / f"{name}.jsonl").write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows), encoding="utf-8")
    summary = {"train_kept": len(tr), "heldout_kept": len(ho),
               "train_skips": dict(Counter(r.get("skip", "kept") for r in rep_tr)),
               "heldout_skips": dict(Counter(r.get("skip", "kept") for r in rep_ho)),
               "filter": {"max_err_rate": MAX_ERR_RATE, "max_repeat": MAX_REPEAT}, "rows": rep_tr + rep_ho}
    (out / "v2_curation_report.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, indent=1))


if __name__ == "__main__":
    main()
