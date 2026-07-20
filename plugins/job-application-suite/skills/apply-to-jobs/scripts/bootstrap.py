#!/usr/bin/env python3
"""Create the isolated runtime used by the job-application skill."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys
import venv


SKILL_ROOT = Path(__file__).resolve().parents[1]
LOCK_FILE = SKILL_ROOT / "requirements.lock"


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
    if not LOCK_FILE.exists():
        raise SystemExit(f"Missing hash-locked requirements file: {LOCK_FILE}")

    root = workspace_root(args.workspace)
    venv_path = root / ".runtime" / "venv"
    venv.EnvBuilder(with_pip=True).create(venv_path)
    python = runtime_python(venv_path)
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--require-hashes",
            "-r",
            str(LOCK_FILE),
        ],
        check=True,
    )
    print(f"Runtime ready: {python}")


if __name__ == "__main__":
    main()
