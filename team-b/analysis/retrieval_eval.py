"""Offline retrieval check for the graph tools (Ishan, Team B). No GPU needed.

Re-implements `search_similar_code` / `get_code_neighbors` from HARNESS_README section 6.3 and measures how often
they point at a source file that the reference patch changes (file-hit@k).

Usage (from the repo root):
    python team-b/analysis/retrieval_eval.py --data ../graphdata --split train
    python team-b/analysis/retrieval_eval.py --data ../graphdata --traces harness/runs   # also score the agent's real queries

`--data` must contain graphs/<repo>_<commit>.json and embeddings/<repo>_<commit>.npz from the competition data
(kaggle competitions download gemma-4-developer-agent -f graphs/<key>.json ...).
"""
from __future__ import annotations

import argparse
import ast
import csv
import glob
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
STOP = set("""a an the and or of to in on for with is are be by from as at it this that when not no if fix fixes add
adds added support use using allow update updates make new docs doc pr issue error bug feature should can into
which was were has have type types value values default param params """.split())


# ---------------------------------------------------------------- data
def task_key(t):
    return t["repo"].split("/")[1] + "_" + t["base_commit"]


def changed_files(patch: str):
    files = set(re.findall(r"^diff --git a/(\S+) b/", patch, re.M))
    files |= {f for f in re.findall(r"^\+\+\+ b/(\S+)", patch, re.M)}
    files |= {f for f in re.findall(r"^--- a/(\S+)", patch, re.M)}  # deleted files
    return sorted(files)


def is_source(path: str):
    p = path.replace("\\", "/")
    return p.endswith(".py") and not re.search(r"(^|/)tests?/|(^|/)test_[^/]*\.py$|_test\.py$|conftest\.py$", p)


def module_of(path: str):
    p = path[:-3] if path.endswith(".py") else path
    p = re.sub(r"^src/", "", p)
    if p.endswith("/__init__"):
        p = p[: -len("/__init__")]
    return p.replace("/", ".")


class Repo:
    def __init__(self, data: Path, key: str):
        g = json.load(open(data / "graphs" / f"{key}.json", encoding="utf-8"))
        self.names = [n.get("id", n.get("name")) for n in g["nodes"]]
        self.nameset = set(self.names)
        self.text = {n.get("id", n.get("name")): n.get("text", "") or "" for n in g["nodes"]}
        self.adj = defaultdict(set)
        for e in g["edges"]:
            self.adj[e["source"]].add(e["target"])
            self.adj[e["target"]].add(e["source"])
        z = np.load(data / "embeddings" / f"{key}.npz", allow_pickle=False)
        self.emb_names = list(z.files)
        m = np.stack([z[k] for k in self.emb_names]).astype(np.float32)
        self.emb = m / (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
        self.emb_idx = {k: i for i, k in enumerate(self.emb_names)}
        self.all_names = sorted(self.nameset | set(self.emb_names))

    # 4-tier resolution from the README: exact -> '.'/';'/'/' suffix -> case-insensitive -> substring
    def resolve(self, q: str):
        q = q.strip().strip("`'\"()")
        if not q:
            return None
        if q in self.nameset or q in self.emb_idx:
            return q
        suf = [n for n in self.all_names if any(n.endswith(s + q) for s in ".;/")]
        if suf:
            return min(suf, key=len)
        ql = q.lower()
        ci = [n for n in self.all_names if n.lower() == ql]
        if ci:
            return min(ci, key=len)
        sub = [n for n in self.all_names if q in n]
        return min(sub, key=len) if sub else None

    def search(self, query: str, k: int = 10):
        """Returns (resolved_seed or None, [node names]). Seed is excluded from results (as in the real traces)."""
        seed = self.resolve(query) if " " not in query.strip() else None
        if seed is not None and seed in self.emb_idx:
            sims = self.emb @ self.emb[self.emb_idx[seed]]
            order = np.argsort(-sims)
            return seed, [self.emb_names[i] for i in order if self.emb_names[i] != seed][:k]
        # lexical token-overlap fallback (approximation; the real scorer is not documented)
        toks = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOP and len(w) > 2}
        if not toks:
            return seed, []
        scored = []
        for n in self.all_names:
            nt = set(re.findall(r"[a-z0-9]+", split_camel(n).lower()))
            s = len(toks & nt)
            if s:
                scored.append((-s, len(n), n))
        scored.sort()
        return seed, [n for _, _, n in scored[:k]]

    def neighbors(self, node: str, max_neighbors: int = 50):
        return sorted(self.adj.get(node, ()))[:max_neighbors]


def split_camel(s):
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", s.replace("_", " ").replace(".", " "))


def is_test_node(node: str):
    return bool(re.search(r"(^|\.)tests?(\.|$)|(^|\.)test_\w*|conftest", node))


def node_in(node: str, mods):
    return any(node == m or node.startswith(m + ".") for m in mods)


# ---------------------------------------------------------------- identifier extraction (step 1a of graph-localize)
def candidates(statement: str):
    """Ordered candidate queries, most specific first: dotted names, backticked names, Class.method, CamelCase,
    snake_case, call-like words. Mirrors the prompt's 'most specific symbol name first'."""
    text = re.sub(r"https?://\S+", " ", statement)
    out = []
    ticks = re.findall(r"`([^`\n]{2,80})`", text)
    for t in ticks:
        t = t.strip().rstrip("()")
        if re.fullmatch(r"[A-Za-z_][\w]*(\.[A-Za-z_]\w*)+", t):
            out.append((0, t))
    out += [(1, t) for t in re.findall(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b", text) if not re.search(r"\.(py|md|com|org|io)$", t)]
    for t in ticks:
        t = t.strip().rstrip("()")
        if re.fullmatch(r"[A-Za-z_]\w{2,}", t):
            out.append((2, t))
    out += [(3, t) for t in re.findall(r"\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)+\b", text)]
    out += [(4, t) for t in re.findall(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b", text)]
    out += [(5, t) for t in re.findall(r"\b([A-Za-z_]\w{2,})\(", text)]
    seen, res = set(), []
    for _, t in sorted(out, key=lambda x: x[0]):
        if t not in seen:
            seen.add(t)
            res.append(t)
    return res


def keywords(statement: str, n=3):
    words = [w for w in re.findall(r"[A-Za-z][a-z]{3,}", re.sub(r"https?://\S+", " ", statement)) if w.lower() not in STOP]
    return " ".join(list(dict.fromkeys(w.lower() for w in words))[:n])


def pick_query(repo: Repo, statement: str):
    for c in candidates(statement):
        if len(c) < 4:
            continue
        seed = repo.resolve(c)
        # reject weak substring-only matches of short generic words
        if seed and (c in seed.split(".") or seed.endswith(c) or "." in c or "_" in c or c[:1].isupper()):
            return c, "symbol"
    kw = keywords(statement)
    return (kw, "keywords") if kw else (None, "none")


# ---------------------------------------------------------------- evaluation
def evaluate(tasks, data: Path, k_list=(1, 5, 10)):
    rows, cache = [], {}
    for t in tasks:
        key = task_key(t)
        src = [f for f in changed_files(t["patch"]) if is_source(f)]
        row = {"instance_id": t["instance_id"], "repo": key.split("_")[0], "n_src_files": len(src)}
        if not src:
            row["status"] = "no_source_file"
            rows.append(row)
            continue
        if not (data / "graphs" / f"{key}.json").exists():
            row["status"] = "no_graph"
            rows.append(row)
            continue
        repo = cache.get(key) or cache.setdefault(key, Repo(data, key))
        mods = [module_of(f) for f in src]
        row["in_graph"] = any(node_in(n, mods) for n in repo.all_names)
        q, how = pick_query(repo, t["problem_statement"])
        row.update(query=q, query_type=how)
        if q is None:
            row["status"] = "no_query"
            rows.append(row)
            continue
        seed, res = repo.search(q, k=max(k_list))
        row["status"] = "ok"
        row["seed"] = seed
        row["seed_hit"] = bool(seed and node_in(seed, mods))
        for k in k_list:
            row[f"hit@{k}"] = any(node_in(n, mods) for n in res[:k])
            row[f"seed_or_hit@{k}"] = row["seed_hit"] or row[f"hit@{k}"]
        nt = [n for n in res if not is_test_node(n)]
        row["test_share@5"] = sum(is_test_node(n) for n in res[:5]) / 5
        row["notest_hit@5"] = row["seed_hit"] or any(node_in(n, mods) for n in nt[:5])
        top = res[0] if res else None
        nb = repo.neighbors(top, 15) if top else []
        row["hit@5+nbrs"] = row["seed_or_hit@5"] or any(node_in(n, mods) for n in nb)
        row["top1"] = top
        rows.append(row)
    return rows


def pct(rows, col):
    ok = [r for r in rows if r.get("status") == "ok"]
    return (sum(bool(r.get(col)) for r in ok), len(ok))


# ---------------------------------------------------------------- real agent queries from Kaggle traces
def trace_queries(trace_root: Path):
    out = []
    for f in sorted(glob.glob(str(trace_root / "**" / "trace_*.json"), recursive=True)):
        d = json.load(open(f, encoding="utf-8"))
        iid = Path(f).stem[len("trace_"):]
        variant = Path(f).parts[len(trace_root.parts)]
        for st in d.get("steps", []):
            try:
                calls = ast.literal_eval(st["tool_calls"]) if isinstance(st.get("tool_calls"), str) else st.get("tool_calls") or []
            except Exception:
                continue
            for c in calls:
                if c.get("function_name") == "search_similar_code":
                    obs = st.get("observation", "")
                    names = re.findall(r'"node_name":\s*"([^"]+)"', str(obs).replace('\\"', '"'))
                    out.append({"file": f, "variant": variant, "instance_id": iid,
                                "query": c["arguments"].get("query"), "k": c["arguments"].get("k", 10), "real": names})
                    break
            else:
                continue
            break  # first search call per trace only
    latest = {}
    for q in out:  # files are sorted by run timestamp, so the last one wins
        latest[(q["variant"], q["instance_id"])] = q
    return list(latest.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--split", default="train")
    ap.add_argument("--traces", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "team-b" / "docs" / "retrieval_eval_table.csv")
    a = ap.parse_args()

    ids = open(ROOT / "harness" / "splits" / f"{a.split}.txt").read().split()
    alltasks = {json.loads(l)["instance_id"]: json.loads(l) for l in open(ROOT / "data" / "tasks.jsonl", encoding="utf-8")}
    tasks = [alltasks[i] for i in ids]
    rows = evaluate(tasks, a.data)

    cols = ["instance_id", "repo", "status", "n_src_files", "in_graph", "query_type", "query", "seed", "seed_hit",
            "hit@1", "hit@5", "hit@10", "seed_or_hit@1", "seed_or_hit@5", "seed_or_hit@10", "hit@5+nbrs", "notest_hit@5", "test_share@5", "top1"]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    print(f"split={a.split} tasks={len(rows)} status={dict(Counter(r['status'] for r in rows))}")
    ok = [r for r in rows if r["status"] == "ok"]
    print(f"query types: {dict(Counter(r['query_type'] for r in ok))}")
    print(f"changed module present in graph: {sum(r['in_graph'] for r in ok)}/{len(ok)}")
    groups = {"all": ok, "symbol query": [r for r in ok if r["query_type"] == "symbol"],
              "keyword query": [r for r in ok if r["query_type"] == "keywords"]}
    for repo in sorted({r["repo"] for r in ok}):
        groups[f"repo={repo}"] = [r for r in ok if r["repo"] == repo]
    print(f"{'group':18} {'n':>3} {'seed':>6} {'hit@1':>6} {'hit@5':>6} {'hit@10':>6} {'s|h@1':>6} {'s|h@5':>6} {'+nbrs':>6} {'noTest':>6} {'tests%':>6}")
    for g, rs in groups.items():
        n = len(rs) or 1
        f = lambda c: f"{100 * sum(bool(r.get(c)) for r in rs) / n:5.0f}%"
        print(f"{g:18} {len(rs):>3} {f('seed_hit'):>6} {f('hit@1'):>6} {f('hit@5'):>6} {f('hit@10'):>6} "
              f"{f('seed_or_hit@1'):>6} {f('seed_or_hit@5'):>6} {f('hit@5+nbrs'):>6} {f('notest_hit@5'):>6} {100*sum(r.get('test_share@5',0) for r in rs)/n:5.0f}%")

    if a.traces:
        print("\nAgent's first real search_similar_code call per smoke trace (Kaggle runs):")
        agree, cmp_n, hits = 0, 0, []
        cache = {}
        for q in trace_queries(a.traces):
            t = alltasks.get(q["instance_id"])
            if not t or not q["query"]:
                continue
            key = task_key(t)
            src = [module_of(f) for f in changed_files(t["patch"]) if is_source(f)]
            hit1 = bool(q["real"][:1]) and node_in(q["real"][0], src)
            hit5 = any(node_in(n, src) for n in q["real"][:5])
            seed_hit = False
            if (a.data / "graphs" / f"{key}.json").exists():
                repo = cache.get(key) or cache.setdefault(key, Repo(a.data, key))
                seed, mine = repo.search(q["query"], k=int(q["k"] or 10))
                seed_hit = bool(seed and node_in(seed, src))
                if q["real"]:
                    cmp_n += 1
                    agree += mine[:1] == q["real"][:1]
            hits.append((q["variant"], q["instance_id"], q["query"], seed_hit, hit1, hit5))
            print(f"  {q['variant'][:30]:30} {q['instance_id']:14} q={q['query'][:40]!r:44} seed={seed_hit!s:5} hit@1={hit1!s:5} hit@5={hit5}")
        n = len(hits) or 1
        print(f"  real queries: n={len(hits)}  seed-in-changed-file {sum(h[3] for h in hits)}/{len(hits)}  "
              f"hit@1 {sum(h[4] for h in hits)}/{len(hits)}  hit@5 {sum(h[5] for h in hits)}/{len(hits)}")
        print(f"  reimplementation fidelity: my top-1 == Kaggle top-1 in {agree}/{cmp_n} real calls")


if __name__ == "__main__":
    main()
