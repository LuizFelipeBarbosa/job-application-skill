#!/usr/bin/env python3
"""Run read-only local readiness checks for the job-application suite."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
from urllib.parse import urlsplit


SCHEMA_VERSION = 1
SKILL_ROOT = Path(__file__).resolve().parents[1]
PASSWORD_MANAGER = SKILL_ROOT / "scripts" / "password_manager.py"


def workspace_root(start: Path) -> Path:
    current = start.resolve()
    for directory in (current, *current.parents):
        if (directory / ".git").exists():
            return directory
    return current


def check(check_id: str, status: str, required: bool, message: str, remediation: str = "") -> dict:
    return {
        "id": check_id,
        "status": status,
        "required": required,
        "message": message,
        "remediation": remediation,
    }


def command_version(command: str) -> tuple[tuple[int, ...] | None, str]:
    executable = shutil.which(command)
    if not executable:
        return None, ""
    result = subprocess.run(
        [executable, "--version"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = result.stdout.strip()
    match = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", output)
    if not match:
        return None, output
    return tuple(int(value or 0) for value in match.groups()), output


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def require_exact_keys(value: dict, keys: set[str], label: str) -> None:
    if set(value) != keys:
        raise ValueError(f"{label} fields must be exactly: {', '.join(sorted(keys))}")


def validate_job_sites(value: object) -> None:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("job-sites schema_version must be 1")
    require_exact_keys(value, {"schema_version", "sites"}, "job-sites")
    sites = value.get("sites")
    if not isinstance(sites, list) or not sites:
        raise ValueError("job-sites must contain at least one site")
    site_keys = {
        "id", "name", "enabled", "priority", "browser", "adapter", "capabilities",
        "start_url", "job_search_url", "discovery_hosts", "external_application_sites",
        "instructions",
    }
    seen_ids = set()
    for site in sites:
        if not isinstance(site, dict) or not all(
            isinstance(site.get(key), expected)
            for key, expected in (("id", str), ("name", str), ("enabled", bool), ("priority", int))
        ):
            raise ValueError("job-sites contains an invalid site entry")
        require_exact_keys(site, site_keys, f"job-sites entry {site.get('id', '')}")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", site["id"]) or site["id"] in seen_ids:
            raise ValueError("job-sites IDs must be unique lowercase slugs")
        seen_ids.add(site["id"])
        if site["priority"] < 1 or site["browser"] != "chrome-extension":
            raise ValueError("job-sites priority or browser is invalid")
        if not isinstance(site["adapter"], str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9_-]*", site["adapter"]
        ):
            raise ValueError("job-sites adapter is invalid")
        capabilities = site["capabilities"]
        if not isinstance(capabilities, dict) or not capabilities or not all(
            isinstance(capability, bool) for capability in capabilities.values()
        ):
            raise ValueError("job-sites capabilities must be named booleans")
        require_exact_keys(
            capabilities,
            {"discover_jobs", "hosted_applications", "follow_external_applications"},
            f"job-sites capabilities for {site['id']}",
        )
        hosts = site["discovery_hosts"]
        if not isinstance(hosts, list) or not hosts or not all(
            isinstance(host, str) and re.fullmatch(r"[a-z0-9.-]+", host) for host in hosts
        ):
            raise ValueError("job-sites discovery_hosts is invalid")
        for field in ("start_url", "job_search_url"):
            parsed = urlsplit(site[field]) if isinstance(site[field], str) else None
            if parsed is None or parsed.scheme != "https" or parsed.hostname not in hosts:
                raise ValueError(f"job-sites {field} must use an approved HTTPS host")
        external = site["external_application_sites"]
        if not isinstance(external, dict) or not external or not all(
            isinstance(setting, bool) for setting in external.values()
        ):
            raise ValueError("job-sites external application policy is invalid")
        require_exact_keys(
            external,
            {
                "enabled",
                "require_handshake_job_match",
                "allow_official_employer_careers",
                "allow_employer_ats",
                "allow_external_job_boards_as_discovery",
            },
            f"job-sites external policy for {site['id']}",
        )
        instruction_path = Path(site["instructions"])
        if (
            instruction_path.is_absolute()
            or ".." in instruction_path.parts
            or not (SKILL_ROOT / instruction_path).is_file()
        ):
            raise ValueError("job-sites instructions must reference a bundled skill file")


def validate_integrations(value: object) -> None:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("integrations schema_version must be 1")
    require_exact_keys(
        value, {"schema_version", "email", "browser", "computer_use"}, "integrations"
    )
    email = value.get("email")
    browser = value.get("browser")
    computer_use = value.get("computer_use")
    if not isinstance(email, dict) or email.get("provider") != "gmail":
        raise ValueError("the beta supports only the gmail email provider")
    require_exact_keys(
        email,
        {"provider", "mode", "allowed_operations", "prohibited_operations"},
        "integrations email",
    )
    if email.get("mode") != "read_only_verification":
        raise ValueError("email mode must be read_only_verification")
    if email.get("allowed_operations") != ["profile", "search", "read_selected_message"]:
        raise ValueError("email allowed_operations must remain profile/search/read-only")
    if email.get("prohibited_operations") != [
        "send", "draft", "archive", "delete", "label", "forward"
    ]:
        raise ValueError("email prohibited_operations is incomplete")
    if not isinstance(browser, dict) or browser.get("provider") != "chrome":
        raise ValueError("browser provider must be chrome")
    require_exact_keys(
        browser,
        {"provider", "default_allowed_hosts", "allow_all_sites", "ats_approval"},
        "integrations browser",
    )
    if browser.get("allow_all_sites") is not False:
        raise ValueError("allow_all_sites must remain false")
    if browser.get("ats_approval") != "one_time_per_verified_host":
        raise ValueError("ATS approval must be one_time_per_verified_host")
    if not isinstance(browser.get("default_allowed_hosts"), list):
        raise ValueError("default_allowed_hosts must be a list")
    if not isinstance(computer_use, dict) or computer_use.get("verification_only") is not True:
        raise ValueError("computer_use.verification_only must be true")
    require_exact_keys(
        computer_use,
        {"verification_only", "full_support", "linux_support", "diagnostic_route"},
        "integrations computer_use",
    )
    if computer_use.get("full_support") != ["darwin", "win32"]:
        raise ValueError("computer_use full support platforms are invalid")
    if computer_use.get("linux_support") != "partial":
        raise ValueError("computer_use Linux support must remain partial")
    if computer_use.get("diagnostic_route") != "http://127.0.0.1:3000/diagnostics/browser":
        raise ValueError("computer_use diagnostic route is invalid")


def collect_checks(root: Path) -> tuple[list[dict], bool]:
    checks = []
    config_error = False

    python_supported = (3, 9) <= sys.version_info[:2] < (3, 14)
    checks.append(
        check(
            "python",
            "pass" if python_supported else "fail",
            True,
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "Install Python 3.9 through 3.13." if not python_supported else "",
        )
    )

    node_version, node_output = command_version("node")
    node_supported = node_version is not None and node_version >= (22, 13, 0)
    checks.append(
        check(
            "node",
            "pass" if node_supported else "fail",
            True,
            node_output or "Node.js not found",
            "Install Node.js 22.13 or newer." if not node_supported else "",
        )
    )
    for manager in ("pnpm", "npm"):
        version, output = command_version(manager)
        checks.append(
            check(
                manager,
                "pass" if version else "fail",
                True,
                output or f"{manager} not found",
                f"Install or enable {manager}." if not version else "",
            )
        )

    backend = subprocess.run(
        [sys.executable, str(PASSWORD_MANAGER), "backend"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    checks.append(
        check(
            "credential_vault",
            "pass" if backend.returncode == 0 else "fail",
            True,
            "Secure operating-system credential vault is available"
            if backend.returncode == 0
            else (backend.stderr.strip() or backend.stdout.strip()),
            "Run bootstrap and configure a supported OS credential vault."
            if backend.returncode
            else "",
        )
    )

    if sys.platform == "darwin":
        clipboard_tools = ("pbcopy", "pbpaste")
    elif os.name == "nt":
        clipboard_tools = ("clip.exe", "powershell.exe")
    else:
        pairs = (("wl-copy", "wl-paste"), ("xclip", "xclip"), ("xsel", "xsel"))
        clipboard_tools = next(
            (pair for pair in pairs if all(shutil.which(tool) for tool in pair)), pairs[0]
        )
    missing_clipboard = [tool for tool in clipboard_tools if not shutil.which(tool)]
    checks.append(
        check(
            "clipboard",
            "fail" if missing_clipboard else "pass",
            True,
            "Clipboard read/write tools are available"
            if not missing_clipboard
            else f"Missing clipboard tools: {', '.join(missing_clipboard)}",
            "Install a supported local clipboard read/write pair." if missing_clipboard else "",
        )
    )

    private_path = root / "private"
    if not private_path.exists():
        checks.append(
            check(
                "private_permissions",
                "warn",
                False,
                "private/ does not exist yet",
                "It will be created with private permissions before the first run.",
            )
        )
    elif os.name == "nt":
        acl = subprocess.run(
            ["icacls", str(private_path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        broad_principals = ("everyone:", "builtin\\users:", "authenticated users:")
        broad_access = any(principal in acl.stdout.casefold() for principal in broad_principals)
        secure = acl.returncode == 0 and not broad_access
        checks.append(
            check(
                "private_permissions",
                "pass" if secure else "fail",
                True,
                "private/ Windows ACL is not broadly accessible"
                if secure
                else "private/ has an unavailable or broad Windows ACL",
                "Run the password manager once to apply the current-user-only ACL."
                if not secure
                else "",
            )
        )
    else:
        mode = stat.S_IMODE(private_path.stat().st_mode)
        checks.append(
            check(
                "private_permissions",
                "pass" if mode == 0o700 else "fail",
                True,
                f"private/ mode is {mode:04o}",
                "Set private/ to mode 0700 before storing account metadata." if mode != 0o700 else "",
            )
        )

    config_specs = (
        (
            "job_sites_config",
            root / "config" / "job-sites.json",
            SKILL_ROOT / "config" / "job-sites.default.json",
            validate_job_sites,
        ),
        (
            "integrations_config",
            root / "config" / "integrations.json",
            SKILL_ROOT / "config" / "integrations.default.json",
            validate_integrations,
        ),
    )
    for check_id, workspace_path, default_path, validator in config_specs:
        selected = workspace_path if workspace_path.exists() else default_path
        try:
            validator(load_json(selected))
        except (OSError, json.JSONDecodeError, ValueError) as error:
            config_error = True
            checks.append(
                check(check_id, "fail", True, f"Invalid configuration: {error}", f"Repair {selected}.")
            )
        else:
            checks.append(check(check_id, "pass", True, f"Valid configuration: {selected}"))

    dashboards = (
        ("local_dashboard", root / "dashboard", "pnpm-lock.yaml"),
        ("hosted_dashboard", root / "dashboard-sites", "package-lock.json"),
    )
    for check_id, directory, lock_name in dashboards:
        if not directory.exists():
            checks.append(check(check_id, "warn", False, "Companion dashboard is not installed"))
            continue
        valid = (directory / "package.json").exists() and (directory / lock_name).exists()
        checks.append(
            check(
                check_id,
                "pass" if valid else "fail",
                True,
                "Dashboard manifest and lockfile are present" if valid else "Dashboard package files are incomplete",
                "Restore the dashboard package and lockfile." if not valid else "",
            )
        )
        dependencies_installed = (directory / "node_modules").is_dir()
        checks.append(
            check(
                f"{check_id}_dependencies",
                "pass" if dependencies_installed else "warn",
                False,
                "Dashboard dependencies are installed"
                if dependencies_installed
                else "Dashboard dependencies are not installed",
                "Run the dashboard's frozen package-manager install."
                if not dependencies_installed
                else "",
            )
        )

    if sys.platform in {"darwin", "win32"}:
        checks.append(check("computer_use_platform", "pass", True, "Full Computer Use platform support"))
    else:
        checks.append(
            check(
                "computer_use_platform",
                "warn",
                False,
                "Linux support is partial; full Computer Use is unavailable",
            )
        )
    return checks, config_error


def aggregate_status(checks: list[dict]) -> str:
    if any(item["required"] and item["status"] == "fail" for item in checks):
        return "fail"
    if any(item["status"] == "warn" for item in checks):
        return "warn"
    return "pass"


def exit_code(status: str, config_error: bool) -> int:
    if config_error:
        return 2
    return 1 if status == "fail" else 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args()

    root = workspace_root(args.workspace)
    checks, config_error = collect_checks(root)
    aggregate = aggregate_status(checks)
    result = {"schema_version": SCHEMA_VERSION, "status": aggregate, "checks": checks}
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for item in checks:
            print(f"[{item['status'].upper():4}] {item['id']}: {item['message']}")
            if item["remediation"]:
                print(f"       {item['remediation']}")
        print(f"Overall: {aggregate}")
    raise SystemExit(exit_code(aggregate, config_error))


if __name__ == "__main__":
    main()
