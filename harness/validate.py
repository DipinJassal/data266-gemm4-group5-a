"""Validate a variant folder offline (no GPU, no swegemma needed) and optionally build submission.zip.

    python harness/validate.py variants/dipin-output-trim-v1
    python harness/validate.py variants/dipin-output-trim-v1 --zip submission.zip

Mirrors the checks in data/HARNESS_README.md sections 2-3, plus our team rules:
  - exactly one root config (agent.yaml / agent.yml / root_agent.yaml / root_agent.yml)
  - only allowed file extensions, no symlinks, total size < 3 GiB
  - every !include stays inside the folder (no absolute paths, no '..' escaping the root)
  - every agent (root, sub_agents, agent_tool) uses the single team model
  - only the 9 harness tools or agent_tool references; adapters referenced exist
  - eval_config.yaml budgets fit the ~6 min/task runtime target
  - generate_content_config token limits <= 32,768

Exit code 0 = all checks passed (warnings allowed), 1 = at least one error.
The official compiler (adk_submission.validate_directory) still runs on Kaggle; this is a fast pre-check.
"""

from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

import yaml

TEAM_MODEL = "gemma-4-31b-it-qat-w4a16-ct"  # CLAUDE.md: every agent uses this model
HARNESS_TOOLS = {
    "run_command", "submit_patch", "get_status",
    "read_file", "edit_file", "write_file",
    "get_code_neighbors", "search_similar_code", "get_code_subgraph",
}
ROOT_NAMES = ("agent.yaml", "agent.yml", "root_agent.yaml", "root_agent.yml")
ALLOWED_EXT = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
MAX_TOTAL_BYTES = 3 * 1024**3
MAX_TOKENS = 32768
TARGET_MINUTES_PER_TASK = 6.0  # 12 h / ~120 tasks, setup included
GEN_FORBIDDEN = {"tools", "system_instruction", "http_options", "safety_settings", "response_schema"}


class Checker:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.agents_seen: set[Path] = set()

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    def rel(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(self.root))
        except ValueError:
            return str(p)

    # ---- YAML loading with sandboxed !include -------------------------------------------------
    def load_yaml(self, path: Path, depth: int = 0):
        if depth > 10:
            self.err(f"{self.rel(path)}: !include depth > 10")
            return None
        checker = self

        class Loader(yaml.SafeLoader):
            pass

        def include(loader, node):
            target = loader.construct_scalar(node)
            resolved = checker.resolve_include(path, target)
            if resolved is None:
                return None
            if resolved.suffix in (".yaml", ".yml"):
                return checker.load_yaml(resolved, depth + 1)
            return resolved.read_text(encoding="utf-8")

        Loader.add_constructor("!include", include)
        try:
            return yaml.load(path.read_text(encoding="utf-8"), Loader=Loader)
        except yaml.YAMLError as e:
            self.err(f"{self.rel(path)}: invalid YAML: {e}")
            return None

    def resolve_include(self, from_file: Path, target: str) -> Path | None:
        if not target or "\x00" in target or Path(target).is_absolute():
            self.err(f"{self.rel(from_file)}: illegal include path {target!r}")
            return None
        resolved = (from_file.parent / target).resolve()
        if not resolved.is_relative_to(self.root):
            self.err(f"{self.rel(from_file)}: include {target!r} escapes the submission root")
            return None
        if not resolved.is_file():
            self.err(f"{self.rel(from_file)}: include {target!r} not found")
            return None
        return resolved

    # ---- checks -------------------------------------------------------------------------------
    def check_files(self) -> None:
        total = 0
        for p in self.root.rglob("*"):
            if p.is_symlink():
                self.err(f"symlink not allowed: {self.rel(p)}")
                continue
            if p.is_file():
                if p.name == ".DS_Store" or "__pycache__" in p.parts:
                    self.err(f"junk file (remove before zipping): {self.rel(p)}")
                elif p.suffix.lower() not in ALLOWED_EXT:
                    self.err(f"disallowed extension: {self.rel(p)}")
                total += p.stat().st_size
        if total >= MAX_TOTAL_BYTES:
            self.err(f"total size {total / 1024**3:.2f} GiB >= 3 GiB limit")
        self.total_bytes = total

    def find_root(self) -> Path | None:
        found = [self.root / n for n in ROOT_NAMES if (self.root / n).is_file()]
        if not found:
            self.err("no root config (agent.yaml) at the top of the folder")
            return None
        if len(found) > 1:
            self.err(f"multiple root configs: {[f.name for f in found]}")
        return found[0]

    def check_agent(self, path: Path, cfg, label: str) -> None:
        if path in self.agents_seen:
            return
        self.agents_seen.add(path)
        if not isinstance(cfg, dict):
            self.err(f"{label}: agent config must be a mapping")
            return
        name = cfg.get("name", "?")
        where = f"{label} ({name})"
        cls = cfg.get("agent_class", "LlmAgent")

        if cls == "LlmAgent":
            model = cfg.get("model")
            if model is None:
                self.err(f"{where}: missing 'model'")
            else:
                bare = str(model).split("/")[-1]
                if bare != TEAM_MODEL:
                    self.err(f"{where}: model {model!r} is not the team model {TEAM_MODEL!r}")
            adapter = cfg.get("adapter")
            if adapter:
                ad = self.root / "adapters" / adapter
                if not (ad / "adapter_config.json").is_file() or not (ad / "adapter_model.safetensors").is_file():
                    self.err(f"{where}: adapter {adapter!r} missing adapter_config.json or adapter_model.safetensors")
            self.check_gen(cfg.get("generate_content_config"), where)
            for skill in cfg.get("skills") or []:
                sp = (path.parent / skill).resolve()
                if not sp.is_relative_to(self.root) or not (sp / "SKILL.md").is_file():
                    self.err(f"{where}: skill {skill!r} not found (needs SKILL.md inside the folder)")
        elif cls not in ("SequentialAgent", "ParallelAgent", "LoopAgent"):
            self.err(f"{where}: unknown agent_class {cls!r}")

        for tool in cfg.get("tools") or []:
            if isinstance(tool, str):
                if tool not in HARNESS_TOOLS:
                    self.err(f"{where}: tool {tool!r} is not a harness tool")
            elif isinstance(tool, dict) and "agent_tool" in tool:
                self.follow(path, (tool["agent_tool"] or {}).get("config_path"), f"{where} agent_tool")
            elif isinstance(tool, dict):
                self.check_agent(path, tool, f"{where} inline tool agent")
            else:
                self.err(f"{where}: unrecognised tool entry {tool!r}")
        for sub in cfg.get("sub_agents") or []:
            self.follow(path, (sub or {}).get("config_path"), f"{where} sub_agent")

    def follow(self, from_file: Path, config_path, label: str) -> None:
        if not config_path:
            self.err(f"{label}: missing config_path")
            return
        target = self.resolve_include(from_file, config_path)
        if target is not None:
            self.check_agent(target, self.load_yaml(target), self.rel(target))

    def check_gen(self, gen, where: str) -> None:
        if gen is None:
            return
        if not isinstance(gen, dict):
            self.err(f"{where}: generate_content_config must be a mapping")
            return
        for k in GEN_FORBIDDEN & gen.keys():
            self.err(f"{where}: generate_content_config.{k} is not allowed")
        mot = gen.get("max_output_tokens")
        if mot is not None and not (1 <= int(mot) <= MAX_TOKENS):
            self.err(f"{where}: max_output_tokens {mot} outside 1..{MAX_TOKENS}")
        tb = (gen.get("thinking_config") or {}).get("thinking_budget")
        if tb is not None and not (0 <= int(tb) <= MAX_TOKENS):
            self.err(f"{where}: thinking_budget {tb} outside 0..{MAX_TOKENS}")

    def check_eval_config(self) -> None:
        f = next((self.root / n for n in ("eval_config.yaml", "eval_config.yml") if (self.root / n).is_file()), None)
        if f is None:
            self.warn("no eval_config.yaml: Kaggle defaults apply (60 min / 100 tool calls per task) -- far over the 6 min target")
            return
        cfg = self.load_yaml(f) or {}
        ev = cfg.get("evaluation", cfg)
        minutes = ev.get("max_time_minutes")
        if minutes is None:
            self.warn("eval_config: max_time_minutes not set (default 60 min) -- over the 6 min target")
        elif float(minutes) > TARGET_MINUTES_PER_TASK:
            self.warn(f"eval_config: max_time_minutes={minutes} > {TARGET_MINUTES_PER_TASK} -- 120 tasks may not fit in 12 h")
        self.budget = ev

    def run(self) -> None:
        if not self.root.is_dir():
            self.err(f"{self.root} is not a directory")
            return
        self.check_files()
        root_cfg = self.find_root()
        if root_cfg is not None:
            self.check_agent(root_cfg, self.load_yaml(root_cfg), root_cfg.name)
        self.check_eval_config()


def build_zip(root: Path, out: Path) -> None:
    root = root.resolve()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts:
                zf.write(p, p.relative_to(root).as_posix())
    with zipfile.ZipFile(out) as zf:
        names = zf.namelist()
    assert any(n in ROOT_NAMES for n in names), "agent.yaml is not at the zip root"
    print(f"wrote {out} ({out.stat().st_size / 1024**2:.2f} MiB, {len(names)} files, agent.yaml at root)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variant", type=Path, help="variant folder, e.g. variants/<owner>-<name>-v1")
    ap.add_argument("--zip", type=Path, help="also write submission.zip here if validation passes")
    args = ap.parse_args()

    c = Checker(args.variant)
    c.run()
    for w in c.warnings:
        print(f"WARN  {w}")
    for e in c.errors:
        print(f"ERROR {e}")
    if c.errors:
        print(f"FAIL  {args.variant}: {len(c.errors)} error(s)")
        return 1
    b = getattr(c, "budget", {}) or {}
    print(
        f"OK    {args.variant}: {len(c.agents_seen)} agent(s), {c.total_bytes / 1024**2:.1f} MiB, "
        f"budget time={b.get('max_time_minutes', 'default')} min, tool_calls={b.get('max_tool_calls', 'default')}, "
        f"turns={b.get('max_turns', 'default')}"
    )
    if args.zip:
        build_zip(args.variant, args.zip)
    return 0


if __name__ == "__main__":
    sys.exit(main())
