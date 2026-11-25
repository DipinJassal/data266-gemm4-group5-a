"""Regression tests for Team B Kaggle launcher CLI/metadata (mocked; no real API)."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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


def _load_runner():
    path = KAGGLE_DIR / "kaggle_runner.py"
    spec = importlib.util.spec_from_file_location("team_b_kaggle_runner", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _l4_smi(n: int = 4) -> str:
    return "\n".join(f"GPU {i}: NVIDIA L4 (UUID: GPU-{i})" for i in range(n))


class TestPushKernelCli(unittest.TestCase):
    def test_push_kernel_passes_accelerator_and_pins_verified_metadata(self):
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

        verified = rk.VERIFIED_DOCKER_IMAGE

        with tempfile.TemporaryDirectory() as tmp:
            runner_src = (KAGGLE_DIR / "kaggle_runner.py").read_text(encoding="utf-8")
            fake_tb = Path(tmp) / "team-b" / "kaggle"
            fake_tb.mkdir(parents=True)
            (fake_tb / "kaggle_runner.py").write_text(runner_src, encoding="utf-8")

            with mock.patch.object(rk, "kaggle", side_effect=fake_kaggle), mock.patch.object(
                rk, "TB_KAGGLE", fake_tb
            ), mock.patch.object(rk, "DRY_RUN", None), mock.patch.object(Path, "write_text", spy_write):
                kid = rk.push_kernel(
                    user="test-user",
                    kernel_slug="g5b-eval-team-b-variants-base-smoke",
                    run_config={
                        "variant": "team-b/variants/base",
                        "split": "smoke",
                        "task_ids": [],
                        "max_tasks": 2,
                        "docker_image": verified,
                        "image_verification": "gpu-probe",
                    },
                    model="gemma-4-31b-it-qat-w4a16-ct",
                    dataset="test-user/g5b-agents",
                    machine="NvidiaL4",
                    timeout=None,
                    docker_image=verified,
                )

        self.assertEqual(kid, "test-user/g5b-eval-team-b-variants-base-smoke")
        self.assertEqual(len(captured_cli), 1)
        push_args = captured_cli[0]
        self.assertEqual(push_args[:2], ("kernels", "push"))
        self.assertIn("--accelerator", push_args)
        acc_idx = push_args.index("--accelerator")
        self.assertEqual(push_args[acc_idx + 1], "NvidiaL4")

        meta = json.loads(meta_holder["data"])
        self.assertIs(meta.get("enable_gpu"), True)
        self.assertEqual(meta.get("machine_shape"), "NvidiaL4")
        self.assertIs(meta.get("enable_internet"), False)
        self.assertIs(meta.get("is_private"), True)
        self.assertEqual(meta.get("docker_image"), verified)
        self.assertNotIn("docker_image_pinning_type", meta)
        self.assertEqual(meta.get("competition_sources"), ["gemma-4-developer-agent"])
        self.assertEqual(meta.get("title"), "g5b-eval-team-b-variants-base-smoke")
        self.assertEqual(meta.get("id"), "test-user/g5b-eval-team-b-variants-base-smoke")
        self.assertEqual(meta.get("dataset_sources")[-1], "test-user/g5b-agents")
        # No personal probe username / kernel id required in generated metadata.
        self.assertNotIn("parth2828", meta_holder["data"])

    def test_resolve_defaults_to_probe_verified_image(self):
        rk = _load_run_kaggle()
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in {rk.DOCKER_IMAGE_ENV, rk.IMAGE_VERIFICATION_ENV}
        }
        with mock.patch.dict(os.environ, env, clear=True), redirect_stdout(io.StringIO()):
            got, ver = rk.resolve_docker_image(
                None,
                dry_run=False,
                image_verification=None,
                accept_unverified_image=False,
            )
        self.assertEqual(got, rk.VERIFIED_DOCKER_IMAGE)
        self.assertEqual(ver, "gpu-probe")

    def test_resolve_blocks_github_candidate_without_accept(self):
        rk = _load_run_kaggle()
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                rk.resolve_docker_image(
                    rk.CANDIDATE_V173_DOCKER_IMAGE,
                    dry_run=False,
                    image_verification="github-release-candidate",
                    accept_unverified_image=False,
                )
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("BLOCKER", err.getvalue())

    def test_resolve_gpu_probe_rejects_other_digest(self):
        rk = _load_run_kaggle()
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                rk.resolve_docker_image(
                    "gcr.io/kaggle-private-byod/python@sha256:other",
                    dry_run=False,
                    image_verification="gpu-probe",
                    accept_unverified_image=False,
                )
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("gpu-probe only applies", err.getvalue())

    def test_resolve_allows_verified_notebook_pull_override(self):
        rk = _load_run_kaggle()
        img = "gcr.io/kaggle-private-byod/python@sha256:notebookverified"
        out = io.StringIO()
        with redirect_stdout(out):
            got, ver = rk.resolve_docker_image(
                img,
                dry_run=False,
                image_verification="notebook-pull",
                accept_unverified_image=False,
            )
        self.assertEqual(got, img)
        self.assertEqual(ver, "notebook-pull")

    def test_resolve_docker_image_uses_cli_and_env(self):
        rk = _load_run_kaggle()
        got, ver = rk.resolve_docker_image(
            "img-from-cli",
            dry_run=False,
            image_verification="session-python",
            accept_unverified_image=False,
        )
        self.assertEqual(got, "img-from-cli")
        self.assertEqual(ver, "session-python")
        with mock.patch.dict(
            os.environ,
            {rk.DOCKER_IMAGE_ENV: "img-from-env", rk.IMAGE_VERIFICATION_ENV: "notebook-pull"},
        ), redirect_stdout(io.StringIO()):
            got, ver = rk.resolve_docker_image(
                None,
                dry_run=False,
                image_verification=None,
                accept_unverified_image=False,
            )
            self.assertEqual(got, "img-from-env")
            self.assertEqual(ver, "notebook-pull")

    def test_resolve_docker_image_dry_run_uses_verified_default(self):
        rk = _load_run_kaggle()
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in {rk.DOCKER_IMAGE_ENV, rk.IMAGE_VERIFICATION_ENV}
        }
        with mock.patch.dict(os.environ, env, clear=True), redirect_stdout(io.StringIO()):
            got, ver = rk.resolve_docker_image(
                None,
                dry_run=True,
                image_verification=None,
                accept_unverified_image=False,
            )
            self.assertEqual(got, rk.VERIFIED_DOCKER_IMAGE)
            self.assertEqual(ver, "gpu-probe")

    def test_title_matches_slug(self):
        rk = _load_run_kaggle()
        slug = "g5b-eval-team-b-variants-analyzer-plan-smoke"
        self.assertEqual(rk.kernel_title_for_slug(slug), slug)

    def test_cli_version_gate_blocks_1745(self):
        rk = _load_run_kaggle()
        self.assertFalse(rk.kaggle_cli_reports_docker_image_push_support((1, 7, 4, 5)))
        self.assertTrue(rk.kaggle_cli_reports_docker_image_push_support((2, 2, 5)))
        self.assertEqual(rk.parse_kaggle_cli_version("Kaggle API 1.7.4.5"), (1, 7, 4, 5))
        self.assertEqual(rk.parse_kaggle_cli_version("2.2.5"), (2, 2, 5))

    def test_require_cli_support_dies_when_unsupported(self):
        rk = _load_run_kaggle()
        fake_info = {
            "kaggle_executable": "/tmp/kaggle",
            "version_text": "Kaggle API 1.7.4.5",
            "version": (1, 7, 4, 5),
            "supports_docker_image_push": False,
            "probe": "test",
        }
        err = io.StringIO()
        with mock.patch.object(rk, "probe_kaggle_cli_docker_image_support", return_value=fake_info), redirect_stderr(
            err
        ), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                rk.require_kaggle_cli_docker_image_support(dry_run=False)
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("BLOCKER", err.getvalue())
        self.assertIn("1.7.4.5", err.getvalue())

    def test_require_cli_support_allows_dry_run_without_cli(self):
        rk = _load_run_kaggle()
        fake_info = {
            "kaggle_executable": None,
            "version_text": None,
            "version": None,
            "supports_docker_image_push": False,
            "probe": "missing",
        }
        with mock.patch.object(rk, "probe_kaggle_cli_docker_image_support", return_value=fake_info), redirect_stdout(
            io.StringIO()
        ):
            info = rk.require_kaggle_cli_docker_image_support(dry_run=True)
        self.assertFalse(info["supports_docker_image_push"])


class TestPythonGate(unittest.TestCase):
    def test_require_compatible_python_rejects_313(self):
        runner = _load_runner()
        fake = type("V", (), {"major": 3, "minor": 13, "micro": 15})()
        with mock.patch.object(runner.sys, "version_info", fake):
            with self.assertRaises(SystemExit) as ctx:
                runner.require_compatible_python()
            msg = str(ctx.exception)
            self.assertIn("3.13.15", msg)
            self.assertIn("3.12", msg)

    def test_require_compatible_python_accepts_312(self):
        runner = _load_runner()
        fake = type("V", (), {"major": 3, "minor": 12, "micro": 13})()
        with mock.patch.object(runner.sys, "version_info", fake):
            runner.require_compatible_python()  # no raise

    def test_count_l4_gpus(self):
        runner = _load_runner()
        self.assertEqual(runner.count_l4_gpus(_l4_smi(4)), 4)
        self.assertEqual(runner.count_l4_gpus("GPU 0: NVIDIA T4"), 0)

    def test_runtime_preflight_requires_four_l4(self):
        runner = _load_runner()
        fake_py = type("V", (), {"major": 3, "minor": 12, "micro": 13})()
        with tempfile.TemporaryDirectory() as tmp:
            wh = Path(tmp) / "gemma-4-developer-agent-wheelhouse"
            wh.mkdir()
            (wh / "apache_tvm_ffi-0.1.0-cp312-cp312-linux_x86_64.whl").write_text("x")
            (wh / "other-1.0-py3-none-any.whl").write_text("x")

            with mock.patch.object(runner.sys, "version_info", fake_py), mock.patch.object(
                runner, "find_one", return_value=wh
            ), mock.patch.object(
                runner,
                "_probe_gpu",
                return_value={
                    "nvidia_smi": _l4_smi(4),
                    "l4_count": 4,
                    "cuda_visible_devices": None,
                    "torch_cuda_available": None,
                    "torch_gpu_count": None,
                },
            ), redirect_stdout(io.StringIO()):
                info = runner.runtime_preflight(
                    {
                        "docker_image": "gcr.io/kaggle-private-byod/python@sha256:abc",
                        "image_verification": "gpu-probe",
                        "machine_shape": "NvidiaL4",
                        "required_gpu_count": 4,
                        "required_gpu_name": "L4",
                    }
                )
        self.assertEqual(info["wheels"]["cp312_count"], 1)
        self.assertEqual(info["gpu"]["l4_count"], 4)

    def test_runtime_preflight_rejects_missing_l4(self):
        runner = _load_runner()
        fake_py = type("V", (), {"major": 3, "minor": 12, "micro": 13})()
        with tempfile.TemporaryDirectory() as tmp:
            wh = Path(tmp) / "gemma-4-developer-agent-wheelhouse"
            wh.mkdir()
            (wh / "apache_tvm_ffi-0.1.0-cp312-cp312-linux_x86_64.whl").write_text("x")
            with mock.patch.object(runner.sys, "version_info", fake_py), mock.patch.object(
                runner, "find_one", return_value=wh
            ), mock.patch.object(
                runner,
                "_probe_gpu",
                return_value={
                    "nvidia_smi": "GPU 0: NVIDIA T4",
                    "l4_count": 0,
                    "cuda_visible_devices": None,
                    "torch_cuda_available": None,
                    "torch_gpu_count": None,
                },
            ):
                with self.assertRaises(SystemExit) as ctx:
                    runner.runtime_preflight({"required_gpu_count": 4})
        self.assertIn("L4", str(ctx.exception))
        self.assertIn("required=4", str(ctx.exception))

    def test_runtime_preflight_rejects_313_before_wheels(self):
        runner = _load_runner()
        fake_py = type("V", (), {"major": 3, "minor": 13, "micro": 0})()
        with mock.patch.object(runner.sys, "version_info", fake_py):
            with self.assertRaises(SystemExit) as ctx:
                runner.runtime_preflight({})
        self.assertIn("3.13.0", str(ctx.exception))

    def test_runtime_preflight_rejects_missing_cp312_wheels(self):
        runner = _load_runner()
        fake_py = type("V", (), {"major": 3, "minor": 12, "micro": 13})()
        with tempfile.TemporaryDirectory() as tmp:
            wh = Path(tmp) / "gemma-4-developer-agent-wheelhouse"
            wh.mkdir()
            (wh / "only-cp313-cp313-linux_x86_64.whl").write_text("x")
            with mock.patch.object(runner.sys, "version_info", fake_py), mock.patch.object(
                runner, "find_one", return_value=wh
            ), mock.patch.object(
                runner,
                "_probe_gpu",
                return_value={
                    "nvidia_smi": _l4_smi(4),
                    "l4_count": 4,
                    "cuda_visible_devices": None,
                    "torch_cuda_available": None,
                    "torch_gpu_count": None,
                },
            ):
                with self.assertRaises(SystemExit) as ctx:
                    runner.runtime_preflight({})
        self.assertIn("cp312", str(ctx.exception))


class TestStaleUploadProtection(unittest.TestCase):
    """PR #24 upload_id race fix ported to Team B g5b-agents."""

    def test_make_upload_id_unique(self):
        rk = _load_run_kaggle()
        a, b = rk.make_upload_id(), rk.make_upload_id()
        self.assertNotEqual(a, b)
        self.assertRegex(a, r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")

    def test_stage_dataset_writes_upload_id_and_skips_team_a(self):
        rk = _load_run_kaggle()
        uid = "20261124T000000Z-deadbeef"
        with tempfile.TemporaryDirectory() as tmp:
            stage = Path(tmp) / "dataset"
            rk.stage_dataset("team-b/variants/base", REPO / "team-b/variants/base", stage, upload_id=uid)
            marker = (stage / "G5B_REPO_MARKER").read_text()
            self.assertIn(f"upload_id={uid}", marker)
            self.assertIn("selected_variant=team-b/variants/base", marker)
            self.assertTrue((stage / "team-b" / "variants" / "base" / "agent.yaml").is_file())
            for bad in ("baseline", "variants", "combined", "lora"):
                self.assertFalse((stage / bad).exists())

    def test_verify_mounted_upload_id_ok(self):
        runner = _load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "G5B_REPO_MARKER").write_text(
                "snap\nupload_id=abc-123\nselected_variant=team-b/variants/base\n"
            )
            with redirect_stdout(io.StringIO()):
                runner.verify_mounted_upload_id(repo, {"upload_id": "abc-123"})

    def test_verify_mounted_upload_id_mismatch(self):
        runner = _load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "G5B_REPO_MARKER").write_text("snap\nupload_id=old-version\n")
            with self.assertRaises(SystemExit) as ctx:
                runner.verify_mounted_upload_id(repo, {"upload_id": "new-version"})
            self.assertIn("STALE UPLOAD", str(ctx.exception))
            self.assertIn("new-version", str(ctx.exception))

    def test_verify_mounted_upload_id_missing_marker(self):
        runner = _load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as ctx:
                runner.verify_mounted_upload_id(Path(tmp), {"upload_id": "abc"})
            self.assertIn("STALE UPLOAD", str(ctx.exception))

    def test_verify_mounted_upload_id_missing_config(self):
        runner = _load_runner()
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "G5B_REPO_MARKER").write_text("snap\nupload_id=abc\n")
            with self.assertRaises(SystemExit) as ctx:
                runner.verify_mounted_upload_id(Path(tmp), {})
            self.assertIn("upload_id", str(ctx.exception))

    def test_upload_dataset_dry_run_no_sleep_no_api(self):
        rk = _load_run_kaggle()
        slept: list[float] = []
        kaggle_calls: list[tuple] = []

        def fake_sleep(seconds):
            slept.append(seconds)

        def boom(*args, **kwargs):
            kaggle_calls.append(args)
            raise AssertionError("kaggle must not be called in dry-run")

        dry = REPO / "team-b" / "kaggle" / "runs" / "_dryrun_test_upload_id"
        try:
            dry.mkdir(parents=True, exist_ok=True)
            with mock.patch.object(rk, "DRY_RUN", dry), mock.patch.object(
                rk, "kaggle", side_effect=boom
            ), mock.patch.object(rk.time, "sleep", side_effect=fake_sleep), redirect_stdout(
                io.StringIO()
            ):
                dataset, upload_id = rk.upload_dataset(
                    "test-user",
                    "team-b/variants/base",
                    REPO / "team-b/variants/base",
                    "dry-run message",
                )
            self.assertEqual(dataset, "test-user/g5b-agents")
            self.assertTrue(upload_id)
            self.assertEqual(slept, [])
            self.assertEqual(kaggle_calls, [])
            marker = (dry / "dataset" / "G5B_REPO_MARKER").read_text()
            self.assertIn(f"upload_id={upload_id}", marker)
        finally:
            shutil.rmtree(dry, ignore_errors=True)

    def test_upload_dataset_waits_before_ready_poll_when_previous_ready(self):
        """Simulate previous version still reporting ready; still return new upload_id."""
        rk = _load_run_kaggle()
        slept: list[float] = []
        status_calls = {"n": 0}

        def fake_sleep(seconds):
            slept.append(seconds)

        def fake_kaggle(*args, check=True, timeout=None):
            if args[:2] == ("datasets", "version"):
                return "ok"
            if args[:2] == ("datasets", "status"):
                status_calls["n"] += 1
                return "ready"  # previous version may still look ready
            return "ok"

        with tempfile.TemporaryDirectory() as tmp:
            # Keep DRY_RUN unset so upload path runs; mock subprocess status existence.
            with mock.patch.object(rk, "DRY_RUN", None), mock.patch.object(
                rk, "kaggle", side_effect=fake_kaggle
            ), mock.patch.object(rk.time, "sleep", side_effect=fake_sleep), mock.patch.object(
                rk.subprocess,
                "run",
                return_value=mock.Mock(returncode=0),  # dataset exists → version path
            ), redirect_stdout(io.StringIO()):
                dataset, upload_id = rk.upload_dataset(
                    "test-user",
                    "team-b/variants/base",
                    REPO / "team-b/variants/base",
                    "msg",
                )
        self.assertEqual(dataset, "test-user/g5b-agents")
        self.assertTrue(upload_id)
        self.assertGreaterEqual(len(slept), 1)
        self.assertEqual(slept[0], 90)
        self.assertGreaterEqual(status_calls["n"], 1)

    def test_require_supported_machine_rejects_non_l4(self):
        rk = _load_run_kaggle()
        err = io.StringIO()
        with redirect_stderr(err), self.assertRaises(SystemExit) as ctx:
            rk.require_supported_machine("NvidiaT4")
        self.assertEqual(ctx.exception.code, 1)
        self.assertIn("Unsupported --machine", err.getvalue())
        rk.require_supported_machine("NvidiaL4")  # no raise

    def test_run_config_includes_matching_upload_id_via_push_kernel(self):
        rk = _load_run_kaggle()
        captured: list[str] = []

        def fake_kaggle(*args, check=True, timeout=None):
            return "ok"

        real_write = Path.write_text

        def spy_write(self, data, encoding=None, errors=None, newline=None):
            if self.name == "kaggle_runner.py":
                captured.append(data if isinstance(data, str) else data.decode())
            kwargs = {}
            if encoding is not None:
                kwargs["encoding"] = encoding
            if errors is not None:
                kwargs["errors"] = errors
            if newline is not None:
                kwargs["newline"] = newline
            return real_write(self, data, **kwargs)

        uid = "20261124T120000Z-abcd1234"
        with tempfile.TemporaryDirectory() as tmp:
            fake_tb = Path(tmp) / "team-b" / "kaggle"
            fake_tb.mkdir(parents=True)
            (fake_tb / "kaggle_runner.py").write_text(
                (KAGGLE_DIR / "kaggle_runner.py").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            with mock.patch.object(rk, "kaggle", side_effect=fake_kaggle), mock.patch.object(
                rk, "TB_KAGGLE", fake_tb
            ), mock.patch.object(rk, "DRY_RUN", None), mock.patch.object(Path, "write_text", spy_write):
                rk.push_kernel(
                    user="test-user",
                    kernel_slug="g5b-eval-team-b-variants-base-smoke",
                    run_config={
                        "variant": "team-b/variants/base",
                        "split": "smoke",
                        "upload_id": uid,
                        "docker_image": rk.VERIFIED_DOCKER_IMAGE,
                    },
                    model="gemma-4-31b-it-qat-w4a16-ct",
                    dataset="test-user/g5b-agents",
                    machine="NvidiaL4",
                    timeout=None,
                    docker_image=rk.VERIFIED_DOCKER_IMAGE,
                )
        self.assertTrue(captured)
        self.assertIn(f"'upload_id': '{uid}'", captured[0])


if __name__ == "__main__":
    unittest.main()
