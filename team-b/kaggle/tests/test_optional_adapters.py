"""Regression tests: adapters are required only when referenced (no GPU / no Kaggle)."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

KAGGLE_DIR = Path(__file__).resolve().parents[1]
REPO = KAGGLE_DIR.parents[1]
TEAM_MODEL = "gemma-4-31b-it-qat-w4a16-ct"


def _load_run_kaggle():
    path = KAGGLE_DIR / "run_kaggle.py"
    spec = importlib.util.spec_from_file_location("team_b_run_kaggle_optional_adapters", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / "harness"))
    spec.loader.exec_module(mod)
    return mod


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_scaffold(root: Path) -> None:
    _write(
        root / "eval_config.yaml",
        "evaluation:\n  max_time_minutes: 4.5\n  max_tool_calls: 50\n  max_turns: 50\n",
    )
    _write(
        root / "configs/sampling.yaml",
        "temperature: 0.2\ntop_p: 0.95\nmax_output_tokens: 1024\n",
    )
    _write(root / "prompts/system.md", "Fix the bug.\n")


def _adapter_config(root: Path, name: str, *, with_weights: bool = False) -> None:
    ad = root / "adapters" / name
    _write(
        ad / "adapter_config.json",
        json.dumps({"r": 16, "lora_alpha": 32, "target_modules": ["q_proj"]}, indent=2),
    )
    if with_weights:
        # Tiny non-empty placeholder; validate only checks file presence.
        (ad / "adapter_model.safetensors").write_bytes(b"fake-lora-weights")


class TestCollectReferencedAdapters(unittest.TestCase):
    def test_root_with_no_adapters(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(
                root / "agent.yaml",
                f"name: free_agent\nmodel: {TEAM_MODEL}\ninstruction: !include prompts/system.md\n"
                "tools: [run_command, submit_patch]\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            refs, problems = rk.collect_referenced_adapters(root)
            self.assertEqual(refs, set())
            self.assertEqual(problems, [])

    def test_root_references_main_lora(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(
                root / "agent.yaml",
                f"name: root\nmodel: {TEAM_MODEL}\nadapter: main_lora\n"
                "instruction: !include prompts/system.md\n"
                "tools: [run_command]\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            refs, problems = rk.collect_referenced_adapters(root)
            self.assertEqual(refs, {"main_lora"})
            self.assertEqual(problems, [])

    def test_subagent_via_agent_tool_references_tool_lora(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(root / "prompts/analyzer.md", "Analyze.\n")
            _write(
                root / "sub_agents/code_analyzer.yaml",
                f"name: code_analyzer_agent\nmodel: {TEAM_MODEL}\nadapter: tool_lora\n"
                "instruction: !include ../prompts/analyzer.md\n"
                "tools: [read_file]\n"
                "generate_content_config: !include ../configs/sampling.yaml\n",
            )
            _write(
                root / "agent.yaml",
                f"name: root\nmodel: {TEAM_MODEL}\n"
                "instruction: !include prompts/system.md\n"
                "tools:\n"
                "  - run_command\n"
                "  - agent_tool:\n"
                "      config_path: sub_agents/code_analyzer.yaml\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            refs, problems = rk.collect_referenced_adapters(root)
            self.assertEqual(refs, {"tool_lora"})
            self.assertEqual(problems, [])

    def test_both_adapters_referenced(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(root / "prompts/analyzer.md", "Analyze.\n")
            _write(
                root / "sub_agents/code_analyzer.yaml",
                f"name: code_analyzer_agent\nmodel: {TEAM_MODEL}\nadapter: tool_lora\n"
                "instruction: !include ../prompts/analyzer.md\n"
                "tools: [read_file]\n"
                "generate_content_config: !include ../configs/sampling.yaml\n",
            )
            _write(
                root / "agent.yaml",
                f"name: root\nmodel: {TEAM_MODEL}\nadapter: main_lora\n"
                "instruction: !include prompts/system.md\n"
                "tools:\n"
                "  - run_command\n"
                "  - agent_tool:\n"
                "      config_path: sub_agents/code_analyzer.yaml\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            refs, problems = rk.collect_referenced_adapters(root)
            self.assertEqual(refs, {"main_lora", "tool_lora"})
            self.assertEqual(problems, [])

    def test_malformed_subagent_yaml_is_a_hard_error(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(root / "sub_agents/broken.yaml", "name: [this is: not: valid\n")
            _write(
                root / "agent.yaml",
                f"name: root\nmodel: {TEAM_MODEL}\n"
                "instruction: !include prompts/system.md\n"
                "tools:\n"
                "  - agent_tool:\n"
                "      config_path: sub_agents/broken.yaml\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            refs, problems = rk.collect_referenced_adapters(root)
            self.assertTrue(problems)
            self.assertTrue(any("invalid YAML" in p for p in problems))

    def test_missing_subagent_path_is_a_hard_error(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(
                root / "agent.yaml",
                f"name: root\nmodel: {TEAM_MODEL}\n"
                "instruction: !include prompts/system.md\n"
                "tools:\n"
                "  - agent_tool:\n"
                "      config_path: sub_agents/does_not_exist.yaml\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            refs, problems = rk.collect_referenced_adapters(root)
            self.assertTrue(problems)
            self.assertTrue(any("not found" in p for p in problems))


class TestStructuralAndValidateAdapters(unittest.TestCase):
    def test_adapter_free_variant_without_adapters_dir_passes_structural(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(
                root / "agent.yaml",
                f"name: free_agent\nmodel: {TEAM_MODEL}\n"
                "instruction: !include prompts/system.md\n"
                "tools: [run_command, read_file, submit_patch]\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            self.assertFalse((root / "adapters").exists())
            problems = rk.structural_checks("team-b/variants/tmp-free", root)
            adapter_problems = [p for p in problems if "adapter" in p.lower()]
            self.assertEqual(adapter_problems, [])
            # Shared harness files exist in this repo checkout.
            self.assertTrue(
                all("missing required relative file: adapters/" not in p for p in problems)
            )

    def test_adapter_free_variant_passes_validate(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(
                root / "agent.yaml",
                f"name: free_agent\nmodel: {TEAM_MODEL}\n"
                "instruction: !include prompts/system.md\n"
                "tools: [run_command, read_file, submit_patch]\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            errors, _warnings = rk.validate_variant(root)
            self.assertEqual(errors, [])

    def test_referenced_adapter_missing_config_fails_structural(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(
                root / "agent.yaml",
                f"name: root\nmodel: {TEAM_MODEL}\nadapter: main_lora\n"
                "instruction: !include prompts/system.md\n"
                "tools: [run_command]\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            problems = rk.structural_checks("team-b/variants/tmp", root)
            self.assertTrue(
                any("adapters/main_lora/adapter_config.json" in p for p in problems),
                problems,
            )

    def test_referenced_adapter_missing_weights_fails_validate_not_structural(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _adapter_config(root, "main_lora", with_weights=False)
            _write(
                root / "agent.yaml",
                f"name: root\nmodel: {TEAM_MODEL}\nadapter: main_lora\n"
                "instruction: !include prompts/system.md\n"
                "tools: [run_command, submit_patch]\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            problems = rk.structural_checks("team-b/variants/tmp", root)
            self.assertFalse(
                any("adapter_model.safetensors" in p for p in problems),
                problems,
            )
            self.assertFalse(
                any("adapters/main_lora/adapter_config.json" in p for p in problems),
                problems,
            )
            errors, _warnings = rk.validate_variant(root)
            self.assertTrue(errors)
            self.assertTrue(rk.only_adapter_weight_errors(errors), errors)
            self.assertTrue(all("adapter_model.safetensors" in e for e in errors), errors)

    def test_both_adapters_with_configs_and_weights_pass(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _minimal_scaffold(root)
            _write(root / "prompts/analyzer.md", "Analyze.\n")
            _adapter_config(root, "main_lora", with_weights=True)
            _adapter_config(root, "tool_lora", with_weights=True)
            _write(
                root / "sub_agents/code_analyzer.yaml",
                f"name: code_analyzer_agent\nmodel: {TEAM_MODEL}\nadapter: tool_lora\n"
                "instruction: !include ../prompts/analyzer.md\n"
                "tools: [read_file]\n"
                "generate_content_config: !include ../configs/sampling.yaml\n",
            )
            _write(
                root / "agent.yaml",
                f"name: root\nmodel: {TEAM_MODEL}\nadapter: main_lora\n"
                "instruction: !include prompts/system.md\n"
                "tools:\n"
                "  - run_command\n"
                "  - submit_patch\n"
                "  - agent_tool:\n"
                "      config_path: sub_agents/code_analyzer.yaml\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            problems = rk.structural_checks("team-b/variants/tmp", root)
            self.assertFalse(any("adapter" in p.lower() for p in problems), problems)
            errors, _warnings = rk.validate_variant(root)
            self.assertEqual(errors, [])

    def test_real_base_variant_still_requires_both_adapter_configs(self):
        rk = _load_run_kaggle()
        base = REPO / "team-b" / "variants" / "base"
        refs, problems = rk.collect_referenced_adapters(base)
        self.assertEqual(problems, [])
        self.assertEqual(refs, {"main_lora", "tool_lora"})
        struct = rk.structural_checks("team-b/variants/base", base)
        self.assertFalse(any("adapters/" in p and "missing required" in p for p in struct), struct)


class TestDryRunAdapterMessaging(unittest.TestCase):
    def test_inspect_reports_not_required_for_adapter_free_variant(self):
        rk = _load_run_kaggle()
        with tempfile.TemporaryDirectory() as tmp:
            dry = Path(tmp) / "_dryrun"
            ds = dry / "dataset"
            kn = dry / "kernel"
            variant = "team-b/variants/free"
            selected = ds / variant
            _minimal_scaffold(selected)
            _write(
                selected / "agent.yaml",
                f"name: free_agent\nmodel: {TEAM_MODEL}\n"
                "instruction: !include prompts/system.md\n"
                "tools: [run_command, submit_patch]\n"
                "generate_content_config: !include configs/sampling.yaml\n",
            )
            (ds / "team-b" / "variants").mkdir(parents=True, exist_ok=True)
            # Selected variant also appears under team-b/variants staging layout.
            staged = ds / "team-b" / "variants" / "free"
            if not staged.exists():
                import shutil

                shutil.copytree(selected, staged)
            (ds / "harness" / "splits").mkdir(parents=True)
            (ds / "harness" / "splits" / "smoke.txt").write_text("fastapi_11194\n", encoding="utf-8")
            (ds / "G5B_REPO_MARKER").write_text(
                "data266 group 5 team-b private evaluation snapshot\nupload_id=test-uid\n",
                encoding="utf-8",
            )
            kn.mkdir(parents=True)
            (kn / "kernel-metadata.json").write_text(
                json.dumps(
                    {
                        "id": "dry-run-user/g5b-eval-free-smoke",
                        "title": "g5b-eval-free-smoke",
                        "is_private": True,
                        "enable_internet": False,
                        "enable_gpu": True,
                        "machine_shape": "NvidiaL4",
                        "docker_image": rk.VERIFIED_DOCKER_IMAGE,
                        "competition_sources": [rk.COMPETITION],
                        "dataset_sources": ["dry-run-user/g5b-agents"],
                        "model_sources": [],
                    }
                ),
                encoding="utf-8",
            )
            (kn / "kaggle_runner.py").write_text(
                "RUN_CONFIG = {'upload_id': 'test-uid'}\n"
                "def runtime_preflight():\n    pass\n"
                "def verify_mounted_upload_id():\n    pass\n"
                "G5B_REPO_MARKER = 'x'\n",
                encoding="utf-8",
            )
            buf = io.StringIO()
            with redirect_stdout(buf):
                old = rk.DRY_RUN
                try:
                    rk.DRY_RUN = dry
                    rk.inspect_dry_run_stage(
                        variant,
                        TEAM_MODEL,
                        "dry-run-user",
                        "dry-run-user/g5b-agents",
                        "dry-run-user/g5b-eval-free-smoke",
                    )
                finally:
                    rk.DRY_RUN = old
            out = buf.getvalue()
            self.assertIn("adapter weights in stage: NOT REQUIRED", out)
            self.assertNotIn("MISSING — restore before real Kaggle runs", out)


if __name__ == "__main__":
    unittest.main()
