#!/usr/bin/env python3
"""Create the isolated runtime used by the job-application skill."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


SKILL_ROOT = Path(__file__).resolve().parents[1]
PROJECT_FILE = SKILL_ROOT / "pyproject.toml"
LOCK_FILE = SKILL_ROOT / "uv.lock"


def workspace_root(start: Path) -> Path:
    current = start.resolve()
    for directory in (current, *current.parents):
        if (directory / ".git").exists():
            return directory
    return current


def runtime_python(venv_path: Path) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()

    if not ((3, 9) <= sys.version_info[:2] < (3, 14)):
        raise SystemExit("Python 3.9 through 3.13 is required.")
    if not PROJECT_FILE.exists() or not LOCK_FILE.exists():
        raise SystemExit(f"Missing uv project files under: {SKILL_ROOT}")
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("uv 0.9.29 or newer is required.")

    root = workspace_root(args.workspace)
    venv_path = root / ".runtime" / "venv"
    environment = os.environ.copy()
    environment["UV_PROJECT_ENVIRONMENT"] = str(venv_path)
    subprocess.run(
        [
            uv,
            "sync",
            "--project",
            str(SKILL_ROOT),
            "--locked",
            "--no-dev",
            "--no-install-project",
            "--no-python-downloads",
            "--python",
            sys.executable,
        ],
        env=environment,
        check=True,
    )
    python = runtime_python(venv_path)
    if not python.is_file():
        raise SystemExit(f"uv did not create the expected runtime: {python}")
    print(f"Runtime ready: {python}")


if __name__ == "__main__":
    main()
