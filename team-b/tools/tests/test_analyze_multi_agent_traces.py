"""Deterministic unit tests for multi-agent trace analysis.

All fixtures in this file are SYNTHETIC. They exercise parser / metric logic only.
They are not real Kaggle or swegemma outputs.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analyze_multi_agent_traces import (  # noqa: E402
    NA,
    ToolEvent,
    analyze_events_v1,
    analyze_events_v2,
    analyze_task,
    classify_critic_text,
    extract_events_from_obj,
    gather_trace_payloads,
    main,
    outcome_label,
)


def _events(names: list[str], texts: dict[str, str] | None = None) -> list[ToolEvent]:
    texts = texts or {}
    out: list[ToolEvent] = []
    for i, name in enumerate(names):
        evs: list[ToolEvent] = []
        extract_events_from_obj({"name": name, "text": texts.get(name)}, "synthetic", evs)
        # classify via extract
        if not evs:
            # force classify for bare names
            from analyze_multi_agent_traces import classify_tool_name

            evs = [ToolEvent(index=0, name=name, kind=classify_tool_name(name), text=texts.get(name), source="synthetic")]
        e = evs[0]
        e.index = i
        e.text = texts.get(name, e.text)
        out.append(e)
    return out


class TestOutcome(unittest.TestCase):
    def test_pass_fail_empty_crash(self):
        self.assertEqual(outcome_label({"resolved": True, "patch_chars": 10}), "PASS")
        self.assertEqual(outcome_label({"resolved": False, "patch_chars": 10}), "FAIL")
        self.assertEqual(outcome_label({"resolved": False, "patch_chars": 0}), "EMPTY")
        self.assertEqual(outcome_label({"resolved": False, "error": "HARNESS_CRASH: x", "patch_chars": 0}), "CRASH")
        self.assertEqual(outcome_label({}), NA)


class TestV1Ordering(unittest.TestCase):
    def test_analyzer_before_edit(self):
        ev = _events(["code_analyzer_agent", "read_file", "edit_file"])
        d = analyze_events_v1(ev)
        self.assertTrue(d["analyzer_invoked"])
        self.assertTrue(d["analyzer_before_first_edit"])
        self.assertEqual(d["analyzer_call_count"], 1)
        self.assertEqual(d["analyzer_retry_count"], 0)

    def test_analyzer_after_edit(self):
        ev = _events(["edit_file", "code_analyzer_agent"])
        d = analyze_events_v1(ev)
        self.assertTrue(d["analyzer_invoked"])
        self.assertFalse(d["analyzer_before_first_edit"])

    def test_analyzer_missing(self):
        ev = _events(["read_file", "edit_file", "submit_patch"])
        d = analyze_events_v1(ev)
        self.assertFalse(d["analyzer_invoked"])
        self.assertFalse(d["analyzer_before_first_edit"])
        self.assertEqual(d["analyzer_call_count"], 0)

    def test_structured_plan_and_retry(self):
        ev = _events(
            ["code_analyzer_agent", "code_analyzer_agent", "edit_file"],
            {
                "code_analyzer_agent": "Plan:\n1. files to change: a.py\nRoot cause: missing check",
            },
        )
        # both analyzer events share same text key in helper — rebuild explicitly
        from analyze_multi_agent_traces import classify_tool_name

        ev = [
            ToolEvent(0, "code_analyzer_agent", "analyzer", "Plan:\n1. files to change: foo.py", "synthetic"),
            ToolEvent(1, "code_analyzer_agent", "analyzer", "short", "synthetic"),
            ToolEvent(2, "edit_file", classify_tool_name("edit_file"), None, "synthetic"),
        ]
        d = analyze_events_v1(ev)
        self.assertEqual(d["analyzer_retry_count"], 1)
        self.assertTrue(d["structured_plan_observed"])


class TestV2Critic(unittest.TestCase):
    def test_critic_ok(self):
        cls, n = classify_critic_text("OK\n")
        self.assertEqual(cls, "OK")
        self.assertEqual(n, 0)
        ev = [
            ToolEvent(0, "edit_file", "edit", None, "synthetic"),
            ToolEvent(1, "diff_critic_agent", "critic", "OK", "synthetic"),
            ToolEvent(2, "submit_patch", "submit", None, "synthetic"),
        ]
        d = analyze_events_v2(ev)
        self.assertTrue(d["critic_invoked"])
        self.assertTrue(d["critic_before_submit"])
        self.assertEqual(d["critic_response_class"], "OK")
        self.assertFalse(d["edits_after_critic"])
        self.assertFalse(d["critic_called_more_than_once"])

    def test_critic_multiple_problems_and_edit_after(self):
        text = "Problems:\n1. a.py: wrong status\n2. b.py: missing edge\n3. c.py: empty"
        cls, n = classify_critic_text(text)
        self.assertEqual(cls, "problems")
        self.assertEqual(n, 3)
        ev = [
            ToolEvent(0, "edit_file", "edit", None, "synthetic"),
            ToolEvent(1, "diff_critic_agent", "critic", text, "synthetic"),
            ToolEvent(2, "edit_file", "edit", None, "synthetic"),
            ToolEvent(3, "submit_patch", "submit", None, "synthetic"),
        ]
        d = analyze_events_v2(ev)
        self.assertEqual(d["critic_issue_count"], 3)
        self.assertTrue(d["edits_after_critic"])

    def test_critic_invoked_twice(self):
        ev = [
            ToolEvent(0, "diff_critic_agent", "critic", "OK", "synthetic"),
            ToolEvent(1, "diff_critic_agent", "critic", "OK", "synthetic"),
            ToolEvent(2, "submit_patch", "submit", None, "synthetic"),
        ]
        d = analyze_events_v2(ev)
        self.assertTrue(d["critic_called_more_than_once"])
        self.assertEqual(d["critic_call_count"], 2)


class TestMissingAndMalformed(unittest.TestCase):
    def test_missing_traces_mark_na(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            results = run / "results"
            results.mkdir()
            (results / "harness_results.jsonl").write_text(
                json.dumps(
                    {
                        "instance_id": "demo_1",
                        "repo": "demo/repo",
                        "resolved": False,
                        "wall_seconds": 12.0,
                        "tool_calls": 3,
                        "patch_chars": 0,
                        "error": None,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            t = analyze_task("analyzer-plan", json.loads((results / "harness_results.jsonl").read_text().splitlines()[0]), run, results)
            self.assertEqual(t.trace_status, "missing")
            self.assertEqual(t.analyzer_invoked, NA)
            self.assertEqual(t.analyzer_before_first_edit, NA)
            self.assertFalse(t.non_empty_patch)
            self.assertEqual(t.outcome_label, "EMPTY")

    def test_malformed_task_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            results = run / "results"
            td = results / "task_details"
            td.mkdir(parents=True)
            (results / "harness_results.jsonl").write_text(
                json.dumps({"instance_id": "demo_2", "resolved": True, "patch_chars": 10, "wall_seconds": 1, "tool_calls": 1})
                + "\n",
                encoding="utf-8",
            )
            (td / "demo_2.json").write_text("{not-json", encoding="utf-8")
            row = json.loads((results / "harness_results.jsonl").read_text().splitlines()[0])
            t = analyze_task("diff-critic", row, run, results)
            self.assertEqual(t.trace_status, "missing")
            self.assertTrue(any("malformed JSON" in n for n in t.notes))
            self.assertEqual(t.critic_invoked, NA)

    def test_incomplete_evaluation_partial_rows(self):
        """Partial Kaggle runs: only some tasks present — analyzer still processes what exists."""
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            results = run / "results"
            results.mkdir()
            lines = [
                json.dumps({"instance_id": "a", "resolved": True, "patch_chars": 5, "wall_seconds": 2, "tool_calls": 4}),
                json.dumps({"instance_id": "b", "resolved": False, "patch_chars": 0, "wall_seconds": 9, "tool_calls": 8}),
            ]
            (results / "harness_results.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
            out = run / "out"
            rc = main(["--run-dir", str(run), "--variant", "analyzer-plan", "--output-dir", str(out)])
            self.assertEqual(rc, 0)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["counts"]["tasks"], 2)
            self.assertEqual(summary["counts"]["resolved_true"], 1)
            self.assertTrue((out / "per_task.csv").is_file())
            self.assertTrue((out / "report.md").is_file())

    def test_missing_outcome_labels(self):
        t = analyze_task(
            "analyzer-plan",
            {"instance_id": "x"},  # no resolved / patch fields
            Path("."),
            None,
        )
        self.assertEqual(t.outcome_label, NA)
        self.assertEqual(t.non_empty_patch, NA)


class TestEventExtractionShapes(unittest.TestCase):
    def test_function_call_shape(self):
        payload = {
            "events": [
                {"function_call": {"name": "code_analyzer_agent"}},
                {"function_call": {"name": "edit_file"}},
                {"functionCall": {"name": "submit_patch"}},
            ]
        }
        evs: list[ToolEvent] = []
        extract_events_from_obj(payload, "synthetic", evs)
        names = [e.name for e in evs]
        self.assertIn("code_analyzer_agent", names)
        self.assertIn("edit_file", names)
        self.assertIn("submit_patch", names)
        # Nested wrappers must not double-count each call.
        self.assertEqual(names.count("code_analyzer_agent"), 1)
        self.assertEqual(names.count("edit_file"), 1)
        self.assertEqual(names.count("submit_patch"), 1)


class TestReviewerRegressions(unittest.TestCase):
    """Regressions for the four bugs reproduced in Naveen's PR #18 review."""

    def test_nested_function_call_not_double_counted(self):
        payload = {"function_call": {"name": "edit_file", "args": {"path": "a.py"}}}
        evs: list[ToolEvent] = []
        extract_events_from_obj(payload, "synthetic", evs)
        self.assertEqual([e.name for e in evs], ["edit_file"])
        self.assertEqual(len(evs), 1)

    def test_task_id_matching_is_exact_not_substring(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            results = run / "results"
            traces = results / "swegemma" / "traces"
            traces.mkdir(parents=True)
            (traces / "demo_10.json").write_text(
                json.dumps({"name": "edit_file"}), encoding="utf-8"
            )
            (traces / "demo_1.json").write_text(
                json.dumps({"name": "read_file"}), encoding="utf-8"
            )
            payloads, _notes = gather_trace_payloads(run, results, "demo_1")
            rels = [rel for rel, _ in payloads]
            self.assertEqual(rels, ["results/swegemma/traces/demo_1.json"])
            self.assertFalse(any("demo_10" in rel for rel in rels))

            row = {"instance_id": "demo_1", "resolved": False, "patch_chars": 0}
            t = analyze_task("analyzer-plan", row, run, results)
            self.assertEqual(t.trace_status, "present")
            self.assertEqual(t.trace_sources, ["results/swegemma/traces/demo_1.json"])

    def test_ordering_unknown_without_edit_or_submit(self):
        v1 = analyze_events_v1(
            [ToolEvent(0, "code_analyzer_agent", "analyzer", None, "synthetic")]
        )
        self.assertTrue(v1["analyzer_invoked"])
        self.assertEqual(v1["analyzer_before_first_edit"], NA)

        v2 = analyze_events_v2(
            [ToolEvent(0, "diff_critic_agent", "critic", "OK", "synthetic")]
        )
        self.assertTrue(v2["critic_invoked"])
        self.assertEqual(v2["critic_before_submit"], NA)

    def test_trace_only_input_builds_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            td = run / "task_details"
            td.mkdir()
            (td / "fastapi_11194.json").write_text(
                json.dumps(
                    {
                        "events": [
                            {"name": "code_analyzer_agent", "text": "Plan: files to change"},
                            {"name": "edit_file"},
                            {"name": "submit_patch"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            out = run / "out"
            rc = main(
                [
                    "--run-dir",
                    str(run),
                    "--variant",
                    "analyzer-plan",
                    "--output-dir",
                    str(out),
                ]
            )
            self.assertEqual(rc, 0)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["counts"]["tasks"], 1)
            self.assertEqual(summary["counts"]["trace_status"].get("present"), 1)
            # No harness_results → do not invent resolution metrics.
            self.assertEqual(summary["counts"]["resolved_known"], 0)
            self.assertEqual(summary["counts"]["resolved_true"], NA)
            csv_text = (out / "per_task.csv").read_text(encoding="utf-8")
            self.assertIn("fastapi_11194", csv_text)
            report = (out / "report.md").read_text(encoding="utf-8")
            self.assertIn("fastapi_11194", report)


if __name__ == "__main__":
    unittest.main()
