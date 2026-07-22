#!/usr/bin/env python3
"""Validate the public-beta repository and plugin packaging contract."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "job-application-suite"
SKILL = PLUGIN / "skills" / "apply-to-jobs"
EXPECTED_VERSION = "0.1.0-beta.1"
GMAIL_CONNECTOR_ID = "connector_2128aebfecb84f64a069897515042a44"


def load_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def validate() -> list[str]:
    errors = []
    required_files = (
        ROOT / "LICENSE",
        ROOT / "SECURITY.md",
        ROOT / "PRIVACY.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "CHANGELOG.md",
        ROOT / "docs" / "PLATFORM_SUPPORT.md",
        ROOT / "docs" / "BETA_LIMITATIONS.md",
        ROOT / "docs" / "BETA_ACCEPTANCE.md",
        SKILL / "SKILL.md",
        SKILL / "pyproject.toml",
        SKILL / "uv.lock",
        ROOT / "dashboard-sites" / "VENDORED_SOURCE.md",
    )
    for path in required_files:
        if not path.is_file():
            errors.append(f"Missing required file: {path.relative_to(ROOT)}")

    try:
        manifest = load_json(PLUGIN / ".codex-plugin" / "plugin.json")
        if manifest.get("name") != "job-application-suite":
            errors.append("Plugin name is invalid")
        if manifest.get("version") != EXPECTED_VERSION:
            errors.append("Plugin version is invalid")
        if manifest.get("license") != "MIT":
            errors.append("Plugin license must be MIT")
        if manifest.get("skills") != "./skills/":
            errors.append("Plugin must use its canonical skills directory")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"Invalid plugin manifest: {error}")

    try:
        app_mapping = load_json(PLUGIN / ".app.json").get("apps", {}).get("gmail", {})
        if app_mapping != {"id": GMAIL_CONNECTOR_ID}:
            errors.append("Plugin must require only the official Gmail connector mapping")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"Invalid app mapping: {error}")

    try:
        marketplace = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
        entries = marketplace.get("plugins", [])
        matching = [entry for entry in entries if entry.get("name") == "job-application-suite"]
        source = matching[0].get("source", {}) if len(matching) == 1 else {}
        if source.get("path") != "./plugins/job-application-suite":
            errors.append("Marketplace source does not point to the canonical plugin")
    except (OSError, json.JSONDecodeError, ValueError) as error:
        errors.append(f"Invalid marketplace: {error}")

    for link in (
        ROOT / ".agents" / "skills" / "apply-to-jobs",
        ROOT / ".claude" / "skills" / "apply-to-jobs",
    ):
        if not link.is_symlink() or link.resolve() != SKILL.resolve():
            errors.append(f"Repo skill link is not canonical: {link.relative_to(ROOT)}")

    if (ROOT / "dashboard-sites" / ".git").exists():
        errors.append("dashboard-sites contains nested Git metadata")
    if (ROOT / "dashboard-sites" / ".openai" / "hosting.json").exists():
        errors.append("dashboard-sites contains real hosting configuration")
    vendored = ROOT / "dashboard-sites" / "VENDORED_SOURCE.md"
    if vendored.exists() and "d2a92aa171cc36a9c14c2c9fc8bef7e8a6b96518" not in vendored.read_text():
        errors.append("Vendored dashboard provenance is incorrect")

    for package_path, manager in (
        (ROOT / "dashboard" / "package.json", "pnpm"),
        (ROOT / "dashboard-sites" / "package.json", "npm"),
    ):
        try:
            package = load_json(package_path)
            overrides = package.get("pnpm", {}).get("overrides", {}) if manager == "pnpm" else package.get("overrides", {})
            if overrides.get("postcss") != "8.5.10":
                errors.append(f"{package_path.parent.name} must override PostCSS 8.5.10")
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"Invalid dashboard package: {error}")

    project_text = (SKILL / "pyproject.toml").read_text(encoding="utf-8")
    lock_text = (SKILL / "uv.lock").read_text(encoding="utf-8")
    if 'requires-python = ">=3.9,<3.14"' not in project_text:
        errors.append("Python project does not support the required Python range")
    if '"keyring==25.7.0"' not in project_text:
        errors.append("Python project does not pin keyring 25.7.0")
    if not re.search(
        r'\[\[package\]\]\s+name = "keyring"\s+version = "25\.7\.0"',
        lock_text,
    ):
        errors.append("uv.lock does not lock keyring 25.7.0")
    if 'hash = "sha256:' not in lock_text:
        errors.append("uv.lock does not contain artifact hashes")

    tracked = subprocess.run(
        ["git", "ls-files", "--stage", "dashboard-sites"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if tracked.returncode == 0 and any(line.startswith("160000 ") for line in tracked.stdout.splitlines()):
        errors.append("dashboard-sites is still tracked as a Git link")
    tracked_names = subprocess.run(
        ["git", "ls-files", "dashboard-sites"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    deployment_state = [
        name
        for name in tracked_names.stdout.splitlines()
        if "/.wrangler/" in name or name.endswith("/.openai/hosting.json")
    ]
    if deployment_state:
        errors.append(f"Tracked private deployment state: {', '.join(deployment_state)}")
    return errors


def main() -> None:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print(f"Public-beta release structure is valid ({EXPECTED_VERSION}).")


if __name__ == "__main__":
    main()
