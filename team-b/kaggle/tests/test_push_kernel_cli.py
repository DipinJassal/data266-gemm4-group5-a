"""Regression: kernels push must not pass unsupported --accelerator (Kaggle CLI 1.7.x).

Synthetic / mocked only — never calls the real Kaggle API.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KAGGLE_DIR = Path(__file__).resolve().parents[1]
REPO = KAGGLE_DIR.parents[1]


def _load_run_kaggle():
    path = KAGGLE_DIR / "run_kaggle.py"
    spec = importlib.util.spec_from_file_location("team_b_run_kaggle", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(REPO / "harness"))
    spec.loader.exec_module(mod)
    return mod


class TestPushKernelCli(unittest.TestCase):
    def test_push_kernel_omits_accelerator_keeps_metadata_gpu(self):
        rk = _load_run_kaggle()
        captured_cli: list[tuple] = []
        meta_holder: dict = {}

        def fake_kaggle(*args, check=True, timeout=None):
            captured_cli.append(args)
            return "ok"

        real_write = Path.write_text

        def spy_write(self, data, encoding=None, errors=None, newline=None):
            if self.name == "kernel-metadata.json":
                meta_holder["data"] = data if isinstance(data, str) else data.decode()
            kwargs = {}
            if encoding is not None:
                kwargs["encoding"] = encoding
            if errors is not None:
                kwargs["errors"] = errors
            if newline is not None:
                kwargs["newline"] = newline
            return real_write(self, data, **kwargs)

        with tempfile.TemporaryDirectory() as tmp:
            runner_src = (KAGGLE_DIR / "kaggle_runner.py").read_text(encoding="utf-8")
            fake_tb = Path(tmp) / "team-b" / "kaggle"
            fake_tb.mkdir(parents=True)
            (fake_tb / "kaggle_runner.py").write_text(runner_src, encoding="utf-8")

            with mock.patch.object(rk, "kaggle", side_effect=fake_kaggle), mock.patch.object(
                rk, "TB_KAGGLE", fake_tb
            ), mock.patch.object(rk, "DRY_RUN", None), mock.patch.object(
                rk, "official_docker_image", return_value="test-image"
            ), mock.patch.object(Path, "write_text", spy_write):
                kid = rk.push_kernel(
                    user="test-user",
                    kernel_slug="g5b-eval-team-b-variants-base-smoke",
                    run_config={
                        "variant": "team-b/variants/base",
                        "split": "smoke",
                        "task_ids": [],
                        "max_tasks": 2,
                    },
                    model="gemma-4-31b-it-qat-w4a16-ct",
                    dataset="test-user/g5b-agents",
                    machine="NvidiaL4",
                    timeout=None,
                    allow_network=False,
                )

        self.assertEqual(kid, "test-user/g5b-eval-team-b-variants-base-smoke")
        self.assertEqual(len(captured_cli), 1)
        push_args = captured_cli[0]
        self.assertEqual(push_args[:2], ("kernels", "push"))
        self.assertIn("-p", push_args)
        self.assertNotIn("--accelerator", push_args)
        # machine belongs in metadata only, not as a CLI token
        self.assertNotIn("NvidiaL4", push_args)

        self.assertIn("data", meta_holder)
        meta = json.loads(meta_holder["data"])
        self.assertIs(meta.get("enable_gpu"), True)
        self.assertEqual(meta.get("machine_shape"), "NvidiaL4")
        self.assertIs(meta.get("enable_internet"), False)
        self.assertIs(meta.get("is_private"), True)
        self.assertEqual(meta.get("dataset_sources")[-1], "test-user/g5b-agents")
        self.assertEqual(meta.get("competition_sources"), ["gemma-4-developer-agent"])


if __name__ == "__main__":
    unittest.main()
