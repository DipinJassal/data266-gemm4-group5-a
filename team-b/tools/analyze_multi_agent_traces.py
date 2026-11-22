#!/usr/bin/env python3
"""Analyze saved Team B multi-agent run artifacts (no GPU / no Kaggle launch).

Reads a completed (or partial) evaluation directory produced by
`team-b/kaggle/kaggle_runner.py` / `harness/kaggle_runner.py` and derives
V1 (analyzer-plan) or V2 (diff-critic) metrics from observed tool / sub-agent
events when traces are present.

Example:

    python team-b/tools/analyze_multi_agent_traces.py \\
        --run-dir team-b/kaggle/runs/analyzer-plan/smoke/<UTC>/ \\
        --variant analyzer-plan \\
        --output-dir team-b/analysis/analyzer-plan-smoke-<UTC>/

Does not modify experiment_log.csv, report sections, or slides.
Does not invent missing values: undetermined metrics are marked not_available.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SUPPORTED_VARIANTS = ("analyzer-plan", "diff-critic")

# Harness tools that mutate sources (from Team B base agent.yaml).
EDIT_TOOLS = frozenset({"edit_file", "write_file"})
SUBMIT_TOOLS = frozenset({"submit_patch"})

# Sub-agent names as declared in Parth's V1/V2 YAML (agent `name:` fields).
ANALYZER_AGENT_NAMES = frozenset({"code_analyzer_agent", "code_analyzer"})
CRITIC_AGENT_NAMES = frozenset({"diff_critic_agent", "diff_critic"})

# Text patterns used when a sub-agent response body is available in traces.
PLAN_HINT = re.compile(
    r"(?i)\b(plan|files?\s+to\s+(?:change|edit|modify)|root\s*cause|target\s+files?)\b"
)
CRITIC_OK = re.compile(r"(?im)^\s*OK\s*$")
CRITIC_PROBLEMS = re.compile(r"(?im)^\s*Problems?\s*:")
CRITIC_ISSUE_LINE = re.compile(r"(?m)^\s*\d+\.\s+\S+")

NA = "not_available"


@dataclass
class ToolEvent:
    """One observed tool or sub-agent invocation in order."""

    index: int
    name: str
    kind: str  # "edit" | "submit" | "analyzer" | "critic" | "tool" | "other"
    text: str | None = None
    source: str = "unknown"


@dataclass
class TaskAnalysis:
    instance_id: str
    repo: str | None
    variant: str
    # From harness_results.jsonl when present
    resolved: Any = NA
    wall_seconds: Any = NA
    duration_seconds: Any = NA
    tool_calls_reported: Any = NA
    patch_chars: Any = NA
    error: Any = NA
    outcome_label: str = NA
    # Trace availability
    trace_status: str = "missing"  # present | missing | malformed | partial
    trace_sources: list[str] = field(default_factory=list)
    # Derived (may be NA)
    analyzer_invoked: Any = NA
    analyzer_call_count: Any = NA
    analyzer_before_first_edit: Any = NA
    structured_plan_observed: Any = NA
    analyzer_retry_count: Any = NA
    critic_invoked: Any = NA
    critic_call_count: Any = NA
    critic_before_submit: Any = NA
    critic_response_class: Any = NA  # OK | problems | unknown | NA
    critic_issue_count: Any = NA
    edits_after_critic: Any = NA
    critic_called_more_than_once: Any = NA
    non_empty_patch: Any = NA
    timeout_or_budget_signal: Any = NA
    notes: list[str] = field(default_factory=list)


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and not (isinstance(x, float) and math.isnan(x))


def outcome_label(row: dict) -> str:
    """Mirror harness/summarize.py outcome labels when fields exist."""
    if "resolved" not in row and "patch_chars" not in row and "error" not in row:
        return NA
    if row.get("resolved") is True:
        return "PASS"
    err = str(row.get("error") or "")
    if err.startswith("HARNESS_CRASH"):
        return "CRASH"
    if row.get("patch_chars") in (0, None) and "patch_chars" in row:
        return "EMPTY"
    if row.get("resolved") is False:
        return "FAIL"
    return NA


def timeout_signal(row: dict, events: list[ToolEvent]) -> Any:
    """Best-effort timeout / budget exhaustion signal; never invent."""
    err = str(row.get("error") or "").lower()
    if any(k in err for k in ("timeout", "time limit", "budget", "max_tool", "max_time")):
        return True
    term_notes = " ".join(e.text or "" for e in events if e.text).lower()
    if any(k in term_notes for k in ("timeout", "time limit exceeded", "budget exhausted")):
        return True
    # tool_calls hitting exact budget is only a weak signal → unknown unless error says so
    if err:
        return False
    return NA


def classify_tool_name(name: str) -> str:
    n = name.strip()
    low = n.lower()
    if low in EDIT_TOOLS or low.endswith(".edit_file") or low.endswith(".write_file"):
        return "edit"
    if low in SUBMIT_TOOLS or low.endswith(".submit_patch"):
        return "submit"
    # Sub-agent transfer / agent_tool often uses the agent name.
    for a in ANALYZER_AGENT_NAMES:
        if a in low:
            return "analyzer"
    for c in CRITIC_AGENT_NAMES:
        if c in low:
            return "critic"
    if low in {
        "run_command", "read_file", "get_status", "get_code_neighbors",
        "search_similar_code", "get_code_subgraph", "load_skill",
    }:
        return "tool"
    return "other"


def _maybe_name(obj: dict) -> str | None:
    """Return a tool/agent name from *this* object only (no nested lookup).

    Nested ``function_call`` / ``functionCall`` wrappers are discovered by the
    recursive walker. Looking into them here would emit the same call twice
    (once from the parent, once from the child).
    """
    for key in ("name", "tool", "tool_name", "toolName", "agent_name", "agentName"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _maybe_text(obj: dict) -> str | None:
    for key in ("text", "content", "output", "response", "result", "message"):
        v = obj.get(key)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, list):
            parts = []
            for item in v:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    t = _maybe_text(item)
                    if t:
                        parts.append(t)
            if parts:
                return "\n".join(parts)
    return None


def extract_events_from_obj(obj: Any, source: str, out: list[ToolEvent], seen: set[int] | None = None) -> None:
    """Walk arbitrary JSON and collect ordered tool/agent-like events.

    Schema is not officially frozen in-repo; this walker accepts several observed
    shapes (harness summaries, ADK-like function_call nodes, nested event lists).
    Unrecognized structures yield zero events rather than fabricated ones.
    """
    if seen is None:
        seen = set()
    oid = id(obj)
    if oid in seen:
        return
    seen.add(oid)

    if isinstance(obj, dict):
        name = _maybe_name(obj)
        if name:
            kind = classify_tool_name(name)
            # Skip ultra-generic container names
            if kind != "other" or name.lower() in ANALYZER_AGENT_NAMES | CRITIC_AGENT_NAMES | EDIT_TOOLS | SUBMIT_TOOLS:
                out.append(
                    ToolEvent(
                        index=len(out),
                        name=name,
                        kind=kind if kind != "other" else classify_tool_name(name),
                        text=_maybe_text(obj),
                        source=source,
                    )
                )
        for v in obj.values():
            extract_events_from_obj(v, source, out, seen)
    elif isinstance(obj, list):
        for item in obj:
            extract_events_from_obj(item, source, out, seen)


def find_harness_results(run_dir: Path) -> Path | None:
    if run_dir.is_file() and run_dir.name == "harness_results.jsonl":
        return run_dir
    return next(run_dir.rglob("harness_results.jsonl"), None)


def load_json_safe(path: Path) -> tuple[Any | None, str | None]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "missing"
    except json.JSONDecodeError as e:
        return None, f"malformed JSON: {e}"
    except OSError as e:
        return None, f"read error: {e}"


def gather_trace_payloads(run_dir: Path, results_parent: Path, instance_id: str) -> tuple[list[tuple[str, Any]], list[str]]:
    """Locate per-task detail / trace files. Paths are inferred from Team B runner docs.

    Matching is exact on the task id (filename stem or directory name). Substring
    globs like ``*<instance_id>*.json`` are intentionally avoided so ``demo_1``
    cannot pick up ``demo_10``.
    """
    candidates: list[Path] = []
    # Primary: task_details next to harness_results.jsonl (and under run_dir for trace-only inputs)
    for details_root in (
        results_parent / "task_details",
        run_dir / "task_details",
    ):
        candidates.append(details_root / f"{instance_id}.json")
    # swegemma traces (runner notes traces are written separately)
    for base in (
        results_parent / "swegemma" / "traces",
        results_parent / "traces",
        run_dir / "swegemma" / "traces",
        run_dir / "traces",
    ):
        candidates.append(base / f"{instance_id}.json")
        candidates.append(base / instance_id / "trace.json")
        candidates.append(base / instance_id / "events.json")
        sub = base / instance_id
        if sub.is_dir():
            for p in sorted(sub.rglob("*.json")):
                candidates.append(p)

    payloads: list[tuple[str, Any]] = []
    notes: list[str] = []
    seen: set[Path] = set()
    for path in candidates:
        try:
            path = path.resolve()
        except OSError:
            continue
        if path in seen or not path.is_file():
            continue
        seen.add(path)
        data, err = load_json_safe(path)
        rel = str(path)
        try:
            rel = str(path.relative_to(run_dir.resolve()))
        except ValueError:
            pass
        if err:
            notes.append(f"{rel}: {err}")
            continue
        payloads.append((rel, data))
    return payloads, notes


def discover_trace_only_instance_ids(run_dir: Path) -> list[str]:
    """Exact task ids from task_details/ or traces/ when harness_results.jsonl is absent."""
    ids: list[str] = []
    seen: set[str] = set()
    skip_stems = {"trace", "events", "harness_results", "run_info", "summary"}

    def add(stem: str) -> None:
        stem = stem.strip()
        if not stem or stem in seen or stem in skip_stems:
            return
        seen.add(stem)
        ids.append(stem)

    for details in sorted(run_dir.rglob("task_details")):
        if not details.is_dir():
            continue
        for p in sorted(details.glob("*.json")):
            add(p.stem)

    for traces in sorted(run_dir.rglob("traces")):
        if not traces.is_dir():
            continue
        for p in sorted(traces.glob("*.json")):
            add(p.stem)
        for sub in sorted(p for p in traces.iterdir() if p.is_dir()):
            if (sub / "trace.json").is_file() or (sub / "events.json").is_file():
                add(sub.name)
    return ids


def analyze_events_v1(events: list[ToolEvent]) -> dict[str, Any]:
    analyzer_idxs = [e.index for e in events if e.kind == "analyzer"]
    edit_idxs = [e.index for e in events if e.kind == "edit"]
    out: dict[str, Any] = {
        "analyzer_invoked": bool(analyzer_idxs),
        "analyzer_call_count": len(analyzer_idxs),
        "analyzer_retry_count": max(0, len(analyzer_idxs) - 1) if analyzer_idxs else 0,
    }
    if not events:
        out.update(
            {
                "analyzer_invoked": NA,
                "analyzer_call_count": NA,
                "analyzer_before_first_edit": NA,
                "structured_plan_observed": NA,
                "analyzer_retry_count": NA,
            }
        )
        return out
    if analyzer_idxs and edit_idxs:
        out["analyzer_before_first_edit"] = analyzer_idxs[0] < edit_idxs[0]
    elif analyzer_idxs and not edit_idxs:
        # Analyzer ran, but without an edit event the before/after relation is unknown.
        out["analyzer_before_first_edit"] = NA
    elif not analyzer_idxs:
        out["analyzer_before_first_edit"] = False
    else:
        out["analyzer_before_first_edit"] = NA

    # Structured plan: inspect text on analyzer events when present.
    texts = [e.text for e in events if e.kind == "analyzer" and e.text]
    if not texts:
        out["structured_plan_observed"] = NA
    else:
        out["structured_plan_observed"] = any(PLAN_HINT.search(t) for t in texts)
    return out


def classify_critic_text(text: str) -> tuple[str, Any]:
    if CRITIC_OK.search(text) and not CRITIC_PROBLEMS.search(text):
        return "OK", 0
    if CRITIC_PROBLEMS.search(text):
        issues = CRITIC_ISSUE_LINE.findall(text)
        return "problems", len(issues) if issues else NA
    return "unknown", NA


def analyze_events_v2(events: list[ToolEvent]) -> dict[str, Any]:
    critic_idxs = [e.index for e in events if e.kind == "critic"]
    submit_idxs = [e.index for e in events if e.kind == "submit"]
    out: dict[str, Any] = {
        "critic_invoked": bool(critic_idxs),
        "critic_call_count": len(critic_idxs),
        "critic_called_more_than_once": len(critic_idxs) > 1 if critic_idxs else False,
    }
    if not events:
        out.update(
            {
                "critic_invoked": NA,
                "critic_call_count": NA,
                "critic_before_submit": NA,
                "critic_response_class": NA,
                "critic_issue_count": NA,
                "edits_after_critic": NA,
                "critic_called_more_than_once": NA,
            }
        )
        return out

    if critic_idxs and submit_idxs:
        out["critic_before_submit"] = critic_idxs[0] < submit_idxs[0]
    elif critic_idxs and not submit_idxs:
        # Critic ran, but without a submit event the before/after relation is unknown.
        out["critic_before_submit"] = NA
    elif not critic_idxs:
        out["critic_before_submit"] = False
    else:
        out["critic_before_submit"] = NA

    texts = [e.text for e in events if e.kind == "critic" and e.text]
    if not texts:
        out["critic_response_class"] = NA
        out["critic_issue_count"] = NA
    else:
        # Use the first critic response (protocol: one call).
        cls, n_issues = classify_critic_text(texts[0])
        out["critic_response_class"] = cls
        out["critic_issue_count"] = n_issues

    if critic_idxs:
        first_c = critic_idxs[0]
        out["edits_after_critic"] = any(e.kind == "edit" and e.index > first_c for e in events)
    else:
        out["edits_after_critic"] = False
    return out


def analyze_task(variant: str, row: dict | None, run_dir: Path, results_parent: Path | None) -> TaskAnalysis:
    instance_id = (row or {}).get("instance_id") or "unknown"
    t = TaskAnalysis(
        instance_id=str(instance_id),
        repo=(row or {}).get("repo"),
        variant=variant,
    )
    if row:
        t.resolved = row.get("resolved", NA)
        t.wall_seconds = row.get("wall_seconds", NA)
        t.duration_seconds = row.get("duration_seconds", NA)
        t.tool_calls_reported = row.get("tool_calls", NA)
        t.patch_chars = row.get("patch_chars", NA)
        t.error = row.get("error", NA)
        t.outcome_label = outcome_label(row)
        if _is_number(t.patch_chars):
            t.non_empty_patch = int(t.patch_chars) > 0
        elif t.patch_chars is NA:
            t.non_empty_patch = NA
        else:
            t.non_empty_patch = NA
    else:
        t.notes.append("task missing from harness_results.jsonl")

    events: list[ToolEvent] = []
    if results_parent is None:
        t.trace_status = "missing"
        t.notes.append("harness_results.jsonl parent unknown; cannot locate task_details/traces")
    else:
        payloads, load_notes = gather_trace_payloads(run_dir, results_parent, str(instance_id))
        t.notes.extend(load_notes)
        if not payloads:
            t.trace_status = "missing"
            t.notes.append("no task_details/ or swegemma/traces/ JSON found for this task")
        else:
            malformed = 0
            for rel, data in payloads:
                before = len(events)
                try:
                    extract_events_from_obj(data, rel, events)
                except Exception as e:  # noqa: BLE001 — keep analyzing other tasks
                    malformed += 1
                    t.notes.append(f"event extract failed for {rel}: {type(e).__name__}")
                if len(events) > before:
                    t.trace_sources.append(rel)
            if not t.trace_sources and malformed:
                t.trace_status = "malformed"
            elif not t.trace_sources:
                t.trace_status = "partial"
                t.notes.append("trace files present but no recognizable tool/agent events")
            else:
                t.trace_status = "present"

    # Re-index after extraction
    for i, e in enumerate(events):
        e.index = i

    if variant == "analyzer-plan":
        derived = analyze_events_v1(events) if t.trace_status in {"present", "partial"} else {
            "analyzer_invoked": NA,
            "analyzer_call_count": NA,
            "analyzer_before_first_edit": NA,
            "structured_plan_observed": NA,
            "analyzer_retry_count": NA,
        }
        if t.trace_status == "missing":
            for k in derived:
                derived[k] = NA
        for k, v in derived.items():
            setattr(t, k, v)
    elif variant == "diff-critic":
        derived = analyze_events_v2(events) if t.trace_status in {"present", "partial"} else {
            "critic_invoked": NA,
            "critic_call_count": NA,
            "critic_before_submit": NA,
            "critic_response_class": NA,
            "critic_issue_count": NA,
            "edits_after_critic": NA,
            "critic_called_more_than_once": NA,
        }
        if t.trace_status == "missing":
            for k in derived:
                derived[k] = NA
        for k, v in derived.items():
            setattr(t, k, v)

    t.timeout_or_budget_signal = timeout_signal(row or {}, events)
    return t


def rate(numer: int, denom: int) -> Any:
    if denom <= 0:
        return NA
    return round(numer / denom, 4)


def aggregate(variant: str, tasks: list[TaskAnalysis], run_info: dict, results_path: str | None) -> dict:
    n = len(tasks)
    resolved_known = [t for t in tasks if t.resolved is True or t.resolved is False]
    resolved_true = sum(1 for t in resolved_known if t.resolved is True)

    def count_true(attr: str) -> tuple[int, int]:
        """Return (true_count, known_count)."""
        known = [t for t in tasks if getattr(t, attr) is not NA]
        return sum(1 for t in known if getattr(t, attr) is True), len(known)

    walls = [float(t.wall_seconds) for t in tasks if _is_number(t.wall_seconds)]
    tools = [float(t.tool_calls_reported) for t in tasks if _is_number(t.tool_calls_reported)]
    empty = sum(1 for t in tasks if t.non_empty_patch is False)
    nonempty = sum(1 for t in tasks if t.non_empty_patch is True)
    patch_known = empty + nonempty

    summary: dict[str, Any] = {
        "meta": {
            "variant": variant,
            "n_tasks_in_results": n,
            "run_info": run_info or {},
            "harness_results_path": results_path,
            "schema_notes": [
                "harness_results.jsonl fields observed in-repo samples: instance_id, repo, resolved, "
                "duration_seconds, wall_seconds, tool_calls, test_exit_code, patch_chars, error, total_tokens",
                "Per-task tool order requires task_details/*.json and/or swegemma/traces/*; "
                "Team B runner skips embedding SessionTrace into task_details (see kaggle_runner.save_full_result).",
                "No official frozen swegemma trace schema is checked into this repo; event extraction is best-effort.",
                "edits_after_critic means a source edit occurred after the first critic call; "
                "it does NOT prove the critic feedback was correct or followed faithfully.",
                "Scores here are from the analyzed run directory only — not an official Kaggle leaderboard score.",
            ],
        },
        "counts": {
            "tasks": n,
            "resolved_true": resolved_true if resolved_known else NA,
            "resolved_known": len(resolved_known),
            "non_empty_patch": nonempty if patch_known else NA,
            "empty_patch": empty if patch_known else NA,
            "outcome_labels": dict(Counter(t.outcome_label for t in tasks)),
            "trace_status": dict(Counter(t.trace_status for t in tasks)),
        },
        "runtime": {
            "wall_seconds_avg": round(statistics.mean(walls), 3) if walls else NA,
            "wall_seconds_max": round(max(walls), 3) if walls else NA,
            "tool_calls_avg": round(statistics.mean(tools), 3) if tools else NA,
            "tool_calls_max": round(max(tools), 3) if tools else NA,
            "tasks_with_wall_seconds": len(walls),
            "tasks_with_tool_calls": len(tools),
        },
        "availability": {},
        "metrics": {},
    }

    if variant == "analyzer-plan":
        inv_t, inv_k = count_true("analyzer_invoked")
        bef_t, bef_k = count_true("analyzer_before_first_edit")
        plan_t, plan_k = count_true("structured_plan_observed")
        retries = [t.analyzer_retry_count for t in tasks if _is_number(t.analyzer_retry_count)]
        summary["metrics"] = {
            "analyzer_invocation_rate": rate(inv_t, inv_k),
            "analyzer_invoked_true": inv_t,
            "analyzer_invoked_known": inv_k,
            "analyzer_before_first_edit_rate": rate(bef_t, bef_k),
            "analyzer_before_first_edit_true": bef_t,
            "analyzer_before_first_edit_known": bef_k,
            "structured_plan_rate": rate(plan_t, plan_k),
            "structured_plan_true": plan_t,
            "structured_plan_known": plan_k,
            "analyzer_retry_count_avg": round(statistics.mean(retries), 3) if retries else NA,
        }
        summary["availability"]["analyzer_order_metrics"] = (
            "available" if inv_k else "not_available: need recognizable analyzer/edit events in traces"
        )
    else:
        inv_t, inv_k = count_true("critic_invoked")
        bef_t, bef_k = count_true("critic_before_submit")
        multi_t, multi_k = count_true("critic_called_more_than_once")
        edit_t, edit_k = count_true("edits_after_critic")
        classes = Counter(
            t.critic_response_class for t in tasks if t.critic_response_class not in (NA, None)
        )
        summary["metrics"] = {
            "critic_invocation_rate": rate(inv_t, inv_k),
            "critic_invoked_true": inv_t,
            "critic_invoked_known": inv_k,
            "critic_before_submit_rate": rate(bef_t, bef_k),
            "critic_before_submit_true": bef_t,
            "critic_before_submit_known": bef_k,
            "critic_called_more_than_once_rate": rate(multi_t, multi_k),
            "critic_called_more_than_once_true": multi_t,
            "edits_after_critic_rate": rate(edit_t, edit_k),
            "edits_after_critic_true": edit_t,
            "critic_response_class_counts": dict(classes),
            "note_edits_after_critic": (
                "Observed source edit after first critic call; not proof that feedback was correct."
            ),
        }
        summary["availability"]["critic_order_metrics"] = (
            "available" if inv_k else "not_available: need recognizable critic/submit events in traces"
        )

    timeouts = [t for t in tasks if t.timeout_or_budget_signal is True]
    summary["counts"]["timeout_or_budget_signal_true"] = len(timeouts)
    return summary


def write_csv(path: Path, tasks: list[TaskAnalysis]) -> None:
    if not tasks:
        path.write_text("", encoding="utf-8")
        return
    rows = [asdict(t) for t in tasks]
    # Flatten notes/trace_sources lists
    for r in rows:
        r["notes"] = " | ".join(r.get("notes") or [])
        r["trace_sources"] = " | ".join(r.get("trace_sources") or [])
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def write_markdown(path: Path, variant: str, summary: dict, tasks: list[TaskAnalysis]) -> None:
    m = summary["metrics"]
    c = summary["counts"]
    lines = [
        f"# Multi-agent trace analysis — `{variant}`",
        "",
        "Generated by `team-b/tools/analyze_multi_agent_traces.py`.",
        "",
        "## Scope",
        "",
        "- **Observed:** values read from `harness_results.jsonl` / `run_info.json` / per-task JSON when present.",
        "- **Derived:** ordering metrics from extracted tool/sub-agent events.",
        "- **Unavailable:** fields marked `not_available` when traces or fields are missing.",
        "- **Not a Kaggle leaderboard score.** Use Team B submission history for official scores.",
        "",
        "## Run summary",
        "",
        f"- Tasks in results file: **{c.get('tasks')}**",
        f"- Resolved (known): **{c.get('resolved_true')}** / **{c.get('resolved_known')}**",
        f"- Non-empty patches (known): **{c.get('non_empty_patch')}**; empty: **{c.get('empty_patch')}**",
        f"- Outcome labels: `{c.get('outcome_labels')}`",
        f"- Trace status counts: `{c.get('trace_status')}`",
        f"- Avg wall seconds: **{summary['runtime'].get('wall_seconds_avg')}**; "
        f"avg tool_calls: **{summary['runtime'].get('tool_calls_avg')}**",
        "",
        "## Variant metrics",
        "",
    ]
    for k, v in m.items():
        lines.append(f"- `{k}`: `{v}`")
    lines += ["", "## Schema / limitation notes", ""]
    for note in summary["meta"].get("schema_notes", []):
        lines.append(f"- {note}")
    lines += ["", "## Per-task highlights", ""]
    lines.append("| task | outcome | patch | trace | key metric |")
    lines.append("|---|---|---|---|---|")
    for t in tasks:
        if variant == "analyzer-plan":
            key = f"analyzer_before_edit={t.analyzer_before_first_edit}"
        else:
            key = (
                f"critic={t.critic_response_class}; "
                f"before_submit={t.critic_before_submit}; "
                f"multi={t.critic_called_more_than_once}"
            )
        lines.append(
            f"| {t.instance_id} | {t.outcome_label} | {t.non_empty_patch} | {t.trace_status} | {key} |"
        )
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run-dir", type=Path, required=True, help="saved run directory (contains or nests harness_results.jsonl)")
    ap.add_argument("--variant", required=True, choices=SUPPORTED_VARIANTS)
    ap.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="directory for per_task.csv, summary.json, report.md (e.g. team-b/analysis/<name>/)",
    )
    args = ap.parse_args(argv)

    run_dir = args.run_dir.resolve()
    if not run_dir.exists():
        print(f"ERROR: run dir not found: {run_dir}", file=sys.stderr)
        return 1

    results_path = find_harness_results(run_dir)
    rows: list[dict] = []
    results_parent: Path | None = None
    if results_path is None:
        print(
            "WARN: no harness_results.jsonl under run dir; will still scan for orphan task_details/traces.",
            file=sys.stderr,
        )
    else:
        results_parent = results_path.parent
        for line_no, line in enumerate(results_path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARN: skipping malformed jsonl line {line_no}: {e}", file=sys.stderr)

    info_path = (results_parent / "run_info.json") if results_parent else run_dir / "run_info.json"
    run_info: dict = {}
    if info_path.is_file():
        data, err = load_json_safe(info_path)
        if err:
            print(f"WARN: run_info.json {err}", file=sys.stderr)
        elif isinstance(data, dict):
            run_info = data

    # Trace-only inputs: no harness_results.jsonl (or empty), but task_details/traces exist.
    # Discover exact instance ids and analyze without inventing resolution metrics.
    if not rows:
        orphan_ids = discover_trace_only_instance_ids(run_dir)
        if orphan_ids:
            if results_parent is None:
                results_parent = run_dir
            for iid in orphan_ids:
                rows.append({"instance_id": iid})
            print(
                f"WARN: built {len(rows)} stub task rows from task_details/traces filenames only "
                "(resolution metrics remain not_available).",
                file=sys.stderr,
            )

    tasks = [analyze_task(args.variant, row, run_dir, results_parent) for row in rows]
    results_rel: str | None = None
    if results_path is not None:
        try:
            results_rel = str(results_path.resolve().relative_to(run_dir))
        except ValueError:
            results_rel = str(results_path)
    summary = aggregate(args.variant, tasks, run_info, results_rel)

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "per_task.csv", tasks)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n", encoding="utf-8")
    write_markdown(out / "report.md", args.variant, summary, tasks)

    print(f"Wrote {out / 'per_task.csv'}")
    print(f"Wrote {out / 'summary.json'}")
    print(f"Wrote {out / 'report.md'}")
    print(
        f"Tasks={len(tasks)} trace_present="
        f"{sum(1 for t in tasks if t.trace_status == 'present')} "
        f"resolved_known={summary['counts'].get('resolved_known')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
