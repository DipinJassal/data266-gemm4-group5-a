"""V1 data builder (Bhoomika). Runs INSIDE a Kaggle CPU kernel with the competition attached (snapshots needed).

Turns each train-split task's reference patch into an agent trajectory in the exact format the harness serves:
  system  = the variant's prompts/system.md
  user    = swegemma's build_agent_prompt() text (budget 4.5 min / 50 calls / 50 turns, real workspace tree)
  agent   = run_command(grep) -> read_file(window around the change) -> edit_file per hunk (write_file for new files)
            -> run_command(python3 -m py_compile ...) -> submit_patch -> short final text
  tool    = real tool outputs, computed on the real repo snapshot with swegemma's own edit engine.

Tasks: harness/splits/train.txt minus the 10 smoke tasks (those are held out for eval loss). Dev tasks never appear
(the input dataset only contains train tasks).

Output (/kaggle/working/): v1_train.jsonl, v1_heldout.jsonl (one {"instance_id", "messages", "tools"} per line),
v1_report.json (counts, skips with reasons, token lengths).
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

WORK = Path("/kaggle/working")
T0 = time.time()
REPORT = {"skipped": {}, "built": {}, "errors": {}}

SMOKE = ["fastapi_11194", "fastapi_13537", "fastapi_14609", "fastapi_14962", "fastapi_15763",
         "requests_7505", "rich_3180", "rich_3506", "rich_3782", "rich_4075"]
BUDGET = {"time": 4.5, "calls": 50, "turns": 50, "cmd_timeout": 60}
READ_PAD = 12          # lines of context shown around a change in read_file
MAX_TREE = 200

PROTECTED_RE = re.compile(
    r"(^|/)(test_[^/]*\.py|[^/]*_test\.py|conftest\.py|pytest\.ini|pyproject\.toml|tox\.ini|setup\.cfg|\.pytest\.ini|"
    r"sitecustomize\.py|usercustomize\.py|_swegemma_stubs\.py|[^/]*\.pth)$|(^|/)(tests?|testing)/.*\.py$")
PRUNED = ("docs", "docs_src", "tests", "test_data", "examples", "benchmarks", "assets", "imgs", "questions", "site",
          "g3doc", "google3")


def log(m):
    print(f"[{time.time() - T0:6.1f}s] {m}", flush=True)


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)


def find_one(pattern):
    hits = sorted(glob.glob(pattern, recursive=True))
    if not hits:
        raise SystemExit(f"not found: {pattern}")
    return Path(hits[0])


# ---------------------------------------------------------------- tool schemas (from swegemma.tools docstrings)
def fn(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required}}}


S, I, B = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}
TOOLS = [
    fn("run_command", "Execute a shell command inside the repository sandbox.\n\nYou can run any shell command (Python scripts, tests, git commands, etc.).\nThe command runs in the repository workspace. No network access.\n\nArgs:\n    command: Shell command to execute (e.g., \"pytest tests/\", \"python3 script.py\").",
       {"command": S}, ["command"]),
    fn("read_file", "Read the contents of a file from the repository workspace.\n\nSupports reading specific line ranges using start_line and end_line (1-indexed).\nTo avoid overwhelming the context window, large files are automatically truncated\nto a maximum number of lines (default: 150 lines).\n\nArgs:\n    filepath: Relative path within the workspace directory (e.g., \"fastapi/main.py\", \"pyproject.toml\").\n    start_line: Optional starting line number (1-indexed, inclusive).\n    end_line: Optional ending line number (1-indexed, inclusive).\n\nReturns:\n    Dictionary containing file content, line range, and truncation status.",
       {"filepath": S, "start_line": I, "end_line": I}, ["filepath"]),
    fn("edit_file", "Replace a contiguous block of text in an existing file.\n\nMore token-efficient than write_file for targeted changes. Provide 2-4 lines of unique\nsurrounding context in old_string to ensure an unambiguous match.\n\nArgs:\n    filepath: Relative path to the target file.\n    old_string: Text block to replace.\n    new_string: Replacement text block.\n    allow_multiple: Replace all occurrences of old_string if True.\n\nReturns:\n    Dictionary containing file status, occurrences count, match strategy, and unified diff.",
       {"filepath": S, "old_string": S, "new_string": S, "allow_multiple": B}, ["filepath", "old_string", "new_string"]),
    fn("write_file", "Create or overwrite a file in the workspace.\n\nArgs:\n    filepath: Relative path to the file to create or overwrite.\n    content: Full content of the file.",
       {"filepath": S, "content": S}, ["filepath", "content"]),
    fn("get_status", "Check active budget details (time, tool calls) and active patch details.", {}, []),
    fn("submit_patch", "Capture the current working tree modifications as the agent's submission.\n\nThis generates a unified git diff against the baseline commit. The agent\ncan submit multiple times; only the final submission is evaluated.", {}, []),
    fn("get_code_neighbors", "Discover structural code graph neighbors (callers and callees) for a given code node.\n\nArgs:\n    node: Dotted symbol path or suffix of the function, method, or class node (e.g. 'pkg.module.Class.method', 'Class.method', or 'parse_request').\n    edge_type: Optional edge relation filter (e.g. 'calls', case-insensitive).\n    max_neighbors: Maximum number of neighbor nodes to return (default: 50).\n\nReturns:\n    Dictionary with list of neighbor node names and count.",
       {"node": S, "edge_type": S, "max_neighbors": I}, ["node"]),
    fn("search_similar_code", "Find semantically similar code functions and classes using precomputed graph embeddings.\n\nArgs:\n    query: Dotted symbol path or suffix of a function/method/class in the repository (e.g. 'pkg.module.Class.method', 'Class.method', or 'func_name') to find similar code for. Falls back to lexical keyword matching if no symbol matches.\n    k: Number of most similar code nodes to return (default: 10).\n\nReturns:\n    Dictionary containing matching node names, code snippets, and similarity scores.",
       {"query": S, "k": I}, ["query"]),
    fn("get_code_subgraph", "Extract the relationship graph (nodes and connecting edges) for a focal set of code elements.\n\nArgs:\n    nodes: List of dotted symbol paths or suffix names (e.g. ['pkg.mod.Class.method', 'helper_fn']) to include in the induced subgraph.\n\nReturns:\n    Dictionary detailing the subgraph nodes and connecting directed edges.",
       {"nodes": {"type": "array", "items": S}}, ["nodes"]),
    fn("code_analyzer_agent", "Analyzes repository source files and symbol graphs to locate root causes.", {"request": S}, ["request"]),
]


# ---------------------------------------------------------------- harness prompt (copy of swegemma build_agent_prompt)
def workspace_tree(ws):
    prune = " ".join(f'-not -path "./{d}/*"' for d in PRUNED)
    cmd = (f'find . -mindepth 1 -maxdepth 3 -not -path "./.*" -not -name ".*" -not -name "*.pyc" -not -name "__pycache__" '
           f'-not -path "*/__pycache__/*" -not -path "./*.egg-info*" {prune} '
           f"| awk -F/ '{{print NF, $0}}' | sort -n -k1,1 -k2 | head -{MAX_TREE} | cut -d' ' -f2- | sort")
    return sh(cmd, ws).stdout.rstrip("\n")


def user_prompt(task, tree):
    parts = [f"You are evaluating a software engineering task for repository {task['repo']}.\n\nProblem Statement:\n{task['problem_statement']}\n"]
    parts.append("## Task Budget (Session terminates when any budget is exhausted)\n"
                 f"- Time allowance: {BUDGET['time']} minutes\n- Tool calls allowance: {BUDGET['calls']} calls\n"
                 f"- Max loop iterations: {BUDGET['turns']} turns\n")
    parts.append("## Execution Environment Rules\n"
                 f"- Single command timeout: {BUDGET['cmd_timeout']} seconds (commands exceeding this fail without ending the session)\n"
                 "- Command output limit: 5000 characters\n- File view limit: 150 lines per read_file call\n"
                 "- File character limit: 10000 characters per read_file call\n"
                 "- Environment is offline (no network/PyPI access). All repository and test dependencies are ALREADY pre-installed. Do NOT attempt to run pip install or download packages.\n")
    parts.append("\n".join([
        "## Instructions:",
        "0. All source code is under `/workspace`. Do NOT search outside `/workspace` (e.g. `/usr/`, `/wheels/`, system site-packages). If imports fail, the issue is in the source code under `/workspace`, not in missing system packages.",
        "1. Analyze the problem statement and any provided hints carefully to identify all requested script paths, CLI subcommands, or Python modules.",
        "2. Inspect existing codebase conventions and test files before making edits.",
        "3. Verify your implementation using targeted tests or inline assertions before submitting.",
        "4. Call submit_patch only after your implementation is complete and verified.",
        "5. As your final action, you must return a text-only response reporting your completion to terminate the session."]))
    parts.append("## Code Intelligence Tools\n"
                 "This repository has pre-built code graph and embedding data indexed by dotted symbol path (e.g. `pkg.module.Class.method`). Use these tools for fast, targeted navigation:\n"
                 "- `search_similar_code(query)`: Find functions/classes with similar precomputed embeddings given a symbol name (e.g. `pkg.module.Class.method`, `Class.method`, or `func_name`).\n"
                 "- `get_code_neighbors(node)`: Find callers and callees of a symbol node (e.g. `pkg.module.Class.method` or `Class.method`).\n"
                 "- `get_code_subgraph(nodes)`: Get the induced call subgraph connecting a list of symbol nodes.\n")
    parts.append("## Workspace Layout\nThe repository is located at `/workspace`. Here is the directory tree (up to 3 levels):\n```\n" + tree + "\n```\n")
    return "\n".join(parts)


# ---------------------------------------------------------------- snapshot + patch helpers
def extract_snapshot(snap_dir, task, dest):
    iid, repo = task["instance_id"], task["repo"]
    fb = snap_dir / "fallbacks" / f"{iid}.tgz"
    clean = re.sub(r"[^A-Za-z0-9]+", "_", repo).strip("_")
    bases = [snap_dir / "base_snapshots" / f"base_{clean}.tgz", snap_dir / f"base_{clean}.tgz"]
    bases += [Path(p) for p in glob.glob(str(snap_dir / "**" / f"base_*{repo.split('/')[-1]}*.tgz"), recursive=True)]
    if fb.exists():
        tgz, patch = fb, None
    else:
        tgz = next((b for b in bases if b.exists()), None)
        patch = next((p for p in (snap_dir / "patches" / f"{iid}.patch", snap_dir / f"{iid}.patch") if p.exists()), None)
        if tgz is None:
            tgz = next((p for p in (snap_dir / f"{iid}.tgz", snap_dir / f"{iid}.tar.gz") if p.exists()), None)
            patch = None
    if tgz is None:
        raise RuntimeError("snapshot not found")
    dest.mkdir(parents=True)
    r = sh(f"tar --no-same-owner -xzf {tgz} -C {dest}", dest)
    if r.returncode:
        raise RuntimeError(f"tar failed: {r.stderr[-300:]}")
    if patch is not None and patch.stat().st_size > 0:
        r = sh(f"git apply --binary --whitespace=nowarn {patch} || patch -p1 --batch --forward < {patch}", dest)
        if r.returncode:
            raise RuntimeError(f"snapshot patch failed: {r.stderr[-300:]}")
    for f in ("pytest.ini", "conftest.py"):  # the harness writes these before the agent starts
        if not (dest / f).exists():
            (dest / f).write_text("")
    sh("git init -q 2>/dev/null; git add -A >/dev/null 2>&1; git -c user.email=a@b -c user.name=a commit -qm baseline --allow-empty", dest)


def parse_patch(text):
    """-> list of {path, new, deleted, hunks:[{old_start, old_lines:[...], new_lines:[...]}]}"""
    files, cur, hunk = [], None, None
    rem_old = rem_new = 0
    for line in text.split("\n"):
        if hunk is not None and (rem_old > 0 or rem_new > 0):
            # inside a hunk: use the header counts, so blank context lines ("" after whitespace stripping) are kept
            tag, body = (line[:1], line[1:]) if line else (" ", "")
            if tag == "\\":
                continue
            if tag == " ":
                hunk["old_lines"].append(body); hunk["new_lines"].append(body); rem_old -= 1; rem_new -= 1
            elif tag == "-":
                hunk["old_lines"].append(body); rem_old -= 1
            elif tag == "+":
                hunk["new_lines"].append(body); rem_new -= 1
            else:
                raise ValueError(f"bad hunk line: {line[:40]!r}")
            continue
        if line.startswith("\\"):
            continue
        if line.startswith("diff --git") or line.startswith("index ") or line.startswith("similarity") or line.startswith("rename") \
                or line.startswith("new file mode") or line.startswith("deleted file mode") or line.startswith("old mode") or line.startswith("new mode"):
            if line.startswith(("rename", "similarity")):
                raise ValueError("rename")
            continue
        if line.startswith("Binary files"):
            raise ValueError("binary")
        if line.startswith("--- "):
            cur = {"old": line[4:].strip(), "hunks": []}
            files.append(cur)
            hunk = None
            continue
        if line.startswith("+++ ") and cur is not None and "new_path" not in cur:
            cur["new_path"] = line[4:].strip()
            cur["new"] = cur["old"] == "/dev/null"
            cur["deleted"] = cur["new_path"] == "/dev/null"
            p = cur["new_path"] if not cur["deleted"] else cur["old"]
            cur["path"] = re.sub(r"^[ab]/", "", p)
            continue
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
        if m and cur is not None:
            hunk = {"old_start": int(m.group(1)), "old_lines": [], "new_lines": []}
            rem_old = int(m.group(2)) if m.group(2) is not None else 1
            rem_new = int(m.group(4)) if m.group(4) is not None else 1
            cur["hunks"].append(hunk)
            continue
    return files


def apply_hunks_by_line(content, hunks):
    """Reference result: apply each hunk at its stated line number (checking the old lines match)."""
    lines = content.split("\n")
    offset = 0
    for h in hunks:
        at = h["old_start"] - 1 + offset
        if lines[at:at + len(h["old_lines"])] != h["old_lines"]:
            # stripped trailing whitespace on blank lines: compare ignoring trailing whitespace
            if [l.rstrip() for l in lines[at:at + len(h["old_lines"])]] != [l.rstrip() for l in h["old_lines"]]:
                raise ValueError("reference hunk does not match the snapshot at its line number")
        lines[at:at + len(h["old_lines"])] = h["new_lines"]
        offset += len(h["new_lines"]) - len(h["old_lines"])
    return "\n".join(lines)


def read_window(content, start, end):
    lines = content.splitlines()
    total = len(lines)
    start, end = max(1, start), min(total, end)
    trunc = False
    if end - start + 1 > 150:
        end, trunc = start + 149, True
    snippet = "\n".join(lines[start - 1:end])
    if len(snippet) > 10000:
        snippet, trunc = snippet[:10000], True
    return {"status": "ok", "filepath": None, "content": snippet, "start_line": start, "end_line": end,
            "total_lines": total, "is_truncated": trunc}


IDENT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b")
COMMON = set("self None True False return import from class def async await with else elif yield lambda print value values "
             "data name type list dict str int bool args kwargs result default field fields test tests this that should when "
             "would could which have there their what where".split())


def pick_search_term(task, fpath, content, hunks):
    """An identifier that appears in the issue text and in the target file (prefer ones defined there)."""
    issue = task["problem_statement"]
    in_issue = {t for t in IDENT.findall(issue) if t.lower() not in COMMON}
    defined = set(re.findall(r"^\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", content, re.M))
    near = set()
    for h in hunks:
        near |= set(IDENT.findall("\n".join(h["old_lines"])))
    for pool in (in_issue & defined & near, in_issue & defined, in_issue & near, in_issue & set(IDENT.findall(content))):
        if pool:
            return sorted(pool, key=lambda t: (-len(t), t))[0]
    return None


def compact(d):
    return json.dumps(d, ensure_ascii=False)


# ---------------------------------------------------------------- one task -> one conversation
def build(task, snap_dir, system_prompt, apply_replacement):
    pf = parse_patch(task["patch"])
    if not pf:
        raise ValueError("empty patch")
    kept = []
    for f in pf:
        # these patches mark new files as "--- a/x" with a single "@@ -0,0 +1,N @@" hunk, not "--- /dev/null"
        if len(f["hunks"]) == 1 and f["hunks"][0]["old_start"] == 0 and not f["hunks"][0]["old_lines"]:
            f["new"] = True
        if f.get("deleted"):
            raise ValueError("file deletion")
        if PROTECTED_RE.search(f["path"]):
            continue  # stripped by the harness anyway
        kept.append(f)
    if not kept:
        raise ValueError("only protected files")

    tmp = Path(tempfile.mkdtemp())
    ws = tmp / "ws"
    try:
        extract_snapshot(snap_dir, task, ws)
        tree = workspace_tree(ws)
        msgs = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt(task, tree)}]
        n_call = [0]

        def call(text, name, args, result):
            n_call[0] += 1
            cid = f"call_{n_call[0] * 3}"
            msgs.append({"role": "assistant", "content": text,
                         "tool_calls": [{"id": cid, "type": "function", "function": {"name": name, "arguments": args}}]})
            msgs.append({"role": "tool", "tool_call_id": cid, "name": name, "content": compact(result)})

        # 1. search for the code the issue talks about
        first = next((f for f in kept if not f["new"]), None)
        if first is not None:
            content0 = (ws / first["path"]).read_text(encoding="utf-8", errors="replace")
            term = pick_search_term(task, first["path"], content0, first["hunks"])
            if term:
                top = first["path"].split("/")[0] if "/" in first["path"] else "."
                cmd = f'grep -rn "{term}" {top} --include="*.py" | head -20' if first["path"].endswith(".py") else f'grep -rn "{term}" {top} | head -20'
                r = sh(cmd, ws)
                out = r.stdout[:5000]
                if first["path"] in out:
                    call(f"Let me find where `{term}` is defined in the codebase.", "run_command", {"command": cmd},
                         {"status": "ok", "stdout": out, "stderr": r.stderr[:5000], "exit_code": r.returncode})

        changed_py = []
        for f in kept:
            path = ws / f["path"]
            if f["new"]:
                content = "\n".join(f["hunks"][0]["new_lines"]) + "\n" if f["hunks"] else ""
                call(f"I'll create `{f['path']}`.", "write_file", {"filepath": f["path"], "content": content},
                     {"status": "ok", "filepath": f["path"], "size": len(content)})
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            else:
                with open(path, encoding="utf-8", errors="replace", newline="") as fh:
                    content = fh.read()
                # 2. read a window that covers every hunk of this file (target the change, don't read whole files)
                lo = min(h["old_start"] for h in f["hunks"])
                hi = max(h["old_start"] + max(len(h["old_lines"]), 1) - 1 for h in f["hunks"])
                start, end = max(1, lo - READ_PAD), hi + READ_PAD
                if end - start + 1 > 150:
                    end = start + 149
                res = read_window(content, start, end)
                res["filepath"] = f["path"]
                call(f"Let me look at the relevant part of `{f['path']}`.", "read_file",
                     {"filepath": f["path"], "start_line": res["start_line"], "end_line": res["end_line"]}, res)
                expected = apply_hunks_by_line(content, f["hunks"])
                # 3. one edit_file per hunk, on the live file content, with swegemma's own engine
                offset = 0
                for k, h in enumerate(f["hunks"]):
                    old_l, new_l = list(h["old_lines"]), list(h["new_lines"])
                    if not "\n".join(old_l).strip():
                        raise ValueError("hunk without old context")
                    # if the 3-line diff context is not unique in the file, widen it with real neighbouring lines
                    cur = content.split("\n")
                    at = h["old_start"] - 1 + offset
                    for extra in range(0, 9):
                        try:
                            er = apply_replacement(content, "\n".join(old_l), "\n".join(new_l), filepath=f["path"])
                            break
                        except ValueError as e:
                            if "occurrence" not in str(e) or extra == 8:
                                raise
                            if cur[at:at + len(h["old_lines"])] != h["old_lines"]:
                                raise ValueError("cannot widen context: hunk not at expected line")
                            before = cur[max(0, at - extra - 1):at]
                            after = cur[at + len(h["old_lines"]):at + len(h["old_lines"]) + extra + 1]
                            old_l = before + h["old_lines"] + after
                            new_l = before + h["new_lines"] + after
                    offset += len(h["new_lines"]) - len(h["old_lines"])
                    old_s, new_s = "\n".join(old_l), "\n".join(new_l)
                    if er.strategy != "exact" or er.occurrences != 1:
                        raise ValueError(f"hunk not an exact unique match ({er.strategy}, {er.occurrences})")
                    content = er.new_content
                    diff = er.diff[:5000]
                    text = (f"Now I'll make the change in `{f['path']}`." if k == 0 else "Next, the second part of the change in the same file."
                            if k == 1 else "And the next part of the change.")
                    call(text, "edit_file", {"filepath": f["path"], "old_string": old_s, "new_string": new_s},
                         {"status": "ok", "filepath": f["path"], "occurrences": er.occurrences, "strategy": er.strategy,
                          "diff": diff, "is_truncated": len(er.diff) > 5000})
                if content != expected:
                    raise ValueError("edit_file result differs from the reference patch")
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(content)
            if f["path"].endswith(".py"):
                changed_py.append(f["path"])

        # (sanity check is per file above: the edit_file results must equal the reference hunks applied by line number;
        # `git apply` can't be used because these reference patches have whitespace-stripped blank context lines)

        # 4. quick check that the changed modules still compile
        if changed_py:
            cmd = "python3 -m py_compile " + " ".join(changed_py)
            r = sh(cmd, ws)
            if r.returncode == 0:
                call("Let me make sure the changed files still compile.", "run_command", {"command": cmd},
                     {"status": "ok", "stdout": r.stdout[:5000], "stderr": r.stderr[:5000], "exit_code": 0})
            sh("find . -name __pycache__ -type d -prune -exec rm -rf {} +", ws)

        # 5. submit
        sh("git add -N . >/dev/null 2>&1", ws)
        diff = sh("git diff --binary HEAD", ws).stdout
        nfiles = len(re.findall(r"^diff --git", diff, re.M))
        call("The fix is in place, so I'll submit the patch.", "submit_patch", {},
             {"status": "ok", "patch_size": len(diff), "files_changed": nfiles})
        names = ", ".join(f"`{f['path']}`" for f in kept)
        msgs.append({"role": "assistant", "content": f"I fixed the issue by updating {names} and submitted the patch."})
        return msgs
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    links = [p for pat in ("/kaggle/input/**/gemma-4-developer-agent-wheelhouse", "/kaggle/input/**/g5a-lora-wheels")
             for p in glob.glob(pat, recursive=True) if os.path.isdir(p)]
    pip = [sys.executable, "-m", "pip", "install", "-q", "--no-index"] + [f"--find-links={d}" for d in links]
    subprocess.run(pip + ["--no-deps", "adk-eval-core"], check=True)
    r = subprocess.run(pip + ["transformers==5.23.0"], capture_output=True, text=True)
    REPORT["transformers_install"] = "ok" if r.returncode == 0 else r.stderr[-1500:]
    # swegemma's package __init__ needs adk_submission (not installable here), so use the engine it delegates to:
    # this is swegemma.edit.apply_replacement line for line (adk_eval_core match + make_diff).
    from adk_eval_core.editing import apply_replacement as core_apply, make_diff
    from types import SimpleNamespace

    def apply_replacement(content, old_string, new_string, filepath="file", allow_multiple=False):
        res = core_apply(content, old_string, new_string, allow_multiple=allow_multiple)
        if res.error_message:
            raise ValueError(res.error_message)
        return SimpleNamespace(new_content=res.new_content, diff=make_diff(content, res.new_content, filepath),
                               occurrences=res.occurrences, strategy=res.strategy)

    tasks_path = find_one("/kaggle/input/**/train_tasks.jsonl")
    system_prompt = find_one("/kaggle/input/**/system.md").read_text(encoding="utf-8")
    snap_dir = find_one("/kaggle/input/**/gemma-4-developer-agent/snapshots/**/*.tgz").parent
    while snap_dir.name != "snapshots" and snap_dir != snap_dir.parent:
        snap_dir = snap_dir.parent
    REPORT["snapshot_dir_listing"] = sorted(os.listdir(snap_dir))[:20]
    tasks = [json.loads(l) for l in tasks_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    log(f"{len(tasks)} train tasks, snapshots at {snap_dir}")

    out = {"train": [], "heldout": []}
    for t in tasks:
        iid = t["instance_id"]
        try:
            msgs = build(t, snap_dir, system_prompt, apply_replacement)
            split = "heldout" if iid in SMOKE else "train"
            out[split].append({"instance_id": iid, "messages": msgs, "tools": TOOLS})
            REPORT["built"][iid] = {"split": split, "turns": sum(m["role"] == "assistant" for m in msgs)}
            log(f"ok   {iid} ({split}, {REPORT['built'][iid]['turns']} assistant turns)")
        except ValueError as e:
            REPORT["skipped"][iid] = str(e)
            log(f"skip {iid}: {e}")
        except Exception as e:
            REPORT["errors"][iid] = f"{type(e).__name__}: {e} | {traceback.format_exc()[-600:]}"
            log(f"ERR  {iid}: {e}")

    # token lengths with the served (QAT) chat template
    try:
        from transformers import AutoTokenizer
        qat = find_one("/kaggle/input/**/gemma-4-31b-it-qat-w4a16-ct/*/tokenizer.json").parent
        tok = AutoTokenizer.from_pretrained(qat)
        lens = {}
        for split in out:
            for ex in out[split]:
                txt = tok.apply_chat_template(ex["messages"], tools=ex["tools"], tokenize=False)
                lens[ex["instance_id"]] = len(tok(txt, add_special_tokens=False)["input_ids"])
                ex["n_tokens"] = lens[ex["instance_id"]]
        REPORT["tokens"] = lens
        v = sorted(lens.values())
        REPORT["token_stats"] = {"n": len(v), "min": v[0], "median": v[len(v) // 2], "p90": v[int(len(v) * 0.9)], "max": v[-1],
                                 "total": sum(v)}
        # one rendered example, to check the template output by eye
        ex = out["train"][0]
        (WORK / "rendered_example.txt").write_text(tok.apply_chat_template(ex["messages"], tools=ex["tools"], tokenize=False))
    except Exception as e:
        REPORT["token_error"] = f"{type(e).__name__}: {e} | {traceback.format_exc()[-1500:]}"

    for split in out:
        with (WORK / f"v1_{split}.jsonl").open("w", encoding="utf-8") as fh:
            for ex in out[split]:
                fh.write(json.dumps(ex, ensure_ascii=False) + "\n")
    REPORT["counts"] = {k: len(v) for k, v in out.items()}
    REPORT["n_skipped"], REPORT["n_errors"] = len(REPORT["skipped"]), len(REPORT["errors"])
    (WORK / "v1_report.json").write_text(json.dumps(REPORT, indent=2))
    log(f"done: {REPORT['counts']}, skipped {REPORT['n_skipped']}, errors {REPORT['n_errors']}")


if __name__ == "__main__":
    main()
