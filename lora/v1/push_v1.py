"""Push the V1 training kernel to Kaggle from a laptop.

    python lora/v1/push_v1.py dry     # CPU: tokenize + mask check (no GPU quota)
    python lora/v1/push_v1.py train   # L4 x4: real training (~2-3 h of quota)

Needs the Kaggle CLI and your token. Kernel: <user>/g5a-lora-v1-<mode>.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGE = "gcr.io/kaggle-private-byod/python@sha256:37c64f7dd9c54116ecd1bcc88817c5469b88387388fade02bfa8bf3fc647d461"


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry"
    assert mode in ("dry", "train")
    user = re.search(r"username:\s*(\S+)", subprocess.run([sys.executable, "-m", "kaggle", "config", "view"],
                                                          capture_output=True, text=True).stdout).group(1)
    src = (HERE / "train_v1.py").read_text(encoding="utf-8")
    src, n = re.subn(r'^MODE = "(dry|train)"  #.*$', f'MODE = "{mode}"', src, count=1, flags=re.M)
    assert n == 1
    models = ["google/gemma-4/Other/gemma-4-31b-it-qat-w4a16-ct/2"]
    if mode == "train":
        models.insert(0, "google/gemma-4/transformers/gemma-4-31b-it/1")
    meta = {
        "id": f"{user}/g5a-lora-v1-{mode}", "title": f"g5a-lora-v1-{mode}", "code_file": "train_v1.py",
        "language": "python", "kernel_type": "script", "is_private": True,
        "enable_gpu": mode == "train", "enable_tpu": False, "enable_internet": False, "docker_image": IMAGE,
        "dataset_sources": [f"{user}/g5a-lora-wheels", "metric/gemma-4-developer-agent-wheelhouse"],
        # the competition must be attached: it is what makes Kaggle grant L4 x4 to this account
        "competition_sources": ["gemma-4-developer-agent"],
        "kernel_sources": [f"{user}/g5a-lora-v1-data"],
        "model_sources": models,
    }
    if mode == "train":
        meta["machine_shape"] = "NvidiaL4"
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "train_v1.py").write_text(src, encoding="utf-8")
        (Path(tmp) / "kernel-metadata.json").write_text(json.dumps(meta, indent=2))
        cmd = [sys.executable, "-m", "kaggle", "kernels", "push", "-p", tmp]
        if mode == "train":
            cmd += ["--accelerator", "NvidiaL4"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        print((r.stdout + r.stderr).strip())


if __name__ == "__main__":
    main()
