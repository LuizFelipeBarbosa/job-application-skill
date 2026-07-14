#!/usr/bin/env python3
"""Store job-site passwords in the operating system credential vault."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import string
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

try:
    import keyring
    from keyring.errors import KeyringError, PasswordDeleteError
except ImportError as error:
    raise SystemExit(
        "The local password manager requires the 'keyring' package. "
        "Install the repository requirements before creating an account."
    ) from error


SCHEMA_VERSION = 1
SERVICE_PREFIX = "job-application-skill"
DEFAULT_PASSWORD_LENGTH = 24
PASSWORD_SYMBOLS = "!@#$%^&*()-_=+"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_metadata_path() -> Path:
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        if (directory / ".git").exists():
            return directory / "private" / "accounts.json"
    return current / "private" / "accounts.json"


def normalize_site(value: str) -> str:
    site = value.strip()
    if not site:
        raise SystemExit("Site must not be empty.")

    if "://" in site:
        parsed = urlsplit(site)
        if not parsed.hostname:
            raise SystemExit("Site URL must contain a hostname.")
        site = (parsed.hostname + parsed.path.rstrip("/")).lower()
    else:
        site = re.sub(r"\s+", " ", site.strip("/").lower())

    if not site or any(ord(character) < 32 for character in site):
        raise SystemExit("Site contains invalid characters.")
    return site


def credential_service(site: str) -> str:
    return f"{SERVICE_PREFIX}:{site}"


def normalize_username(value: str) -> str:
    username = value.strip()
    if not username:
        raise SystemExit("Username must not be empty.")
    if any(ord(character) < 32 for character in username):
        raise SystemExit("Username contains invalid characters.")
    return username


def load_metadata(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "accounts": []}

    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Cannot read account metadata at {path}: {error}") from error

    if (
        metadata.get("schema_version") != SCHEMA_VERSION
        or not isinstance(metadata.get("accounts"), list)
    ):
        raise SystemExit(f"Unsupported or invalid account metadata at {path}")
    return metadata


def save_metadata(path: Path, metadata: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary_file:
            temporary_name = temporary_file.name
            json.dump(metadata, temporary_file, indent=2, sort_keys=True)
            temporary_file.write("\n")
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def secure_keyring_backend():
    backend = keyring.get_keyring()
    backend_name = f"{backend.__class__.__module__}.{backend.__class__.__name__}"
    lowered_name = backend_name.lower()
    try:
        priority = backend.priority
    except (AttributeError, RuntimeError) as error:
        raise SystemExit(f"Cannot initialize a secure credential vault: {error}") from error

    insecure_markers = ("fail", "plaintext", "unencrypted")
    if priority <= 0 or any(marker in lowered_name for marker in insecure_markers):
        raise SystemExit(
            "No secure operating-system credential vault is available. "
            "Configure a secure keyring backend; plaintext backends are not allowed."
        )
    return backend, backend_name


def generate_password(length: int, *, include_symbols: bool) -> str:
    if length < 16:
        raise SystemExit("Password length must be at least 16 characters.")
    if length > 128:
        raise SystemExit("Password length must not exceed 128 characters.")

    required = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
    ]
    alphabet = string.ascii_letters + string.digits
    if include_symbols:
        required.append(secrets.choice(PASSWORD_SYMBOLS))
        alphabet += PASSWORD_SYMBOLS

    characters = required + [secrets.choice(alphabet) for _ in range(length - len(required))]
    secrets.SystemRandom().shuffle(characters)
    return "".join(characters)


def find_account(metadata: dict, site: str, username: str) -> dict | None:
    return next(
        (
            account
            for account in metadata["accounts"]
            if account.get("site") == site and account.get("username") == username
        ),
        None,
    )


def copy_to_clipboard(value: str) -> None:
    if sys.platform == "darwin":
        candidates = [(["pbcopy"], "pbcopy")]
    elif os.name == "nt":
        candidates = [(["clip.exe"], "clip.exe")]
    else:
        candidates = [
            (["wl-copy"], "wl-copy"),
            (["xclip", "-selection", "clipboard"], "xclip"),
            (["xsel", "--clipboard", "--input"], "xsel"),
            (["clip.exe"], "clip.exe"),
        ]

    for command, executable in candidates:
        if shutil.which(executable):
            try:
                subprocess.run(
                    command,
                    input=value,
                    text=True,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as error:
                raise SystemExit(f"Clipboard command failed: {executable}") from error
            return
    raise SystemExit("No supported local clipboard command is available.")


def print_json(value: dict) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def generate_credential(args: argparse.Namespace, metadata: dict, metadata_path: Path) -> None:
    _, backend_name = secure_keyring_backend()
    site = normalize_site(args.site)
    username = normalize_username(args.username)

    service = credential_service(site)
    try:
        previous_password = keyring.get_password(service, username)
    except KeyringError as error:
        raise SystemExit(f"Cannot read from the credential vault: {error}") from error
    if previous_password is not None and not args.replace:
        raise SystemExit("A password already exists for this site and username.")

    password = generate_password(args.length, include_symbols=not args.no_symbols)
    try:
        keyring.set_password(service, username, password)
    except KeyringError as error:
        raise SystemExit(f"Cannot write to the credential vault: {error}") from error

    now = utc_now()
    account = find_account(metadata, site, username)
    if account is None:
        account = {
            "site": site,
            "username": username,
            "created_at": now,
            "updated_at": now,
            "permission_confirmed_at": now,
        }
        metadata["accounts"].append(account)
    else:
        account["updated_at"] = now
        account["permission_confirmed_at"] = now

    try:
        save_metadata(metadata_path, metadata)
    except OSError as error:
        try:
            if previous_password is None:
                keyring.delete_password(service, username)
            else:
                keyring.set_password(service, username, previous_password)
        except KeyringError:
            pass
        raise SystemExit(f"Cannot save private account metadata: {error}") from error

    print_json(
        {
            "stored": True,
            "site": site,
            "username": username,
            "backend": backend_name,
            "password_printed": False,
        }
    )


def copy_credential(args: argparse.Namespace) -> None:
    secure_keyring_backend()
    site = normalize_site(args.site)
    username = normalize_username(args.username)
    try:
        password = keyring.get_password(credential_service(site), username)
    except KeyringError as error:
        raise SystemExit(f"Cannot read from the credential vault: {error}") from error
    if password is None:
        raise SystemExit("No password exists for this site and username.")

    copy_to_clipboard(password)
    print_json({"copied": True, "site": site, "username": username, "password_printed": False})


def delete_credential(args: argparse.Namespace, metadata: dict, metadata_path: Path) -> None:
    secure_keyring_backend()
    site = normalize_site(args.site)
    username = normalize_username(args.username)
    try:
        keyring.delete_password(credential_service(site), username)
    except PasswordDeleteError as error:
        raise SystemExit("No password exists for this site and username.") from error
    except KeyringError as error:
        raise SystemExit(f"Cannot delete from the credential vault: {error}") from error

    metadata["accounts"] = [
        account
        for account in metadata["accounts"]
        if not (account.get("site") == site and account.get("username") == username)
    ]
    save_metadata(metadata_path, metadata)
    print_json({"deleted": True, "site": site, "username": username})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help="Override the private non-secret account metadata path.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    generate = commands.add_parser("generate", help="Generate and securely store a password.")
    generate.add_argument("--site", required=True)
    generate.add_argument("--username", required=True)
    generate.add_argument("--length", type=int, default=DEFAULT_PASSWORD_LENGTH)
    generate.add_argument("--no-symbols", action="store_true")
    generate.add_argument("--replace", action="store_true")

    copy = commands.add_parser("copy", help="Copy a stored password without printing it.")
    copy.add_argument("--site", required=True)
    copy.add_argument("--username", required=True)

    delete = commands.add_parser("delete", help="Delete a stored password and its metadata.")
    delete.add_argument("--site", required=True)
    delete.add_argument("--username", required=True)

    commands.add_parser("clear-clipboard", help="Remove the copied password from the clipboard.")
    commands.add_parser("backend", help="Show the active secure credential-vault backend.")
    commands.add_parser("list", help="List non-secret account metadata.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    metadata_path = (args.metadata or default_metadata_path()).expanduser().resolve()

    if args.command == "clear-clipboard":
        copy_to_clipboard("")
        print_json({"clipboard_cleared": True})
        return
    if args.command == "backend":
        _, backend_name = secure_keyring_backend()
        print_json({"backend": backend_name, "secure": True})
        return

    metadata = load_metadata(metadata_path)
    if args.command == "generate":
        generate_credential(args, metadata, metadata_path)
    elif args.command == "copy":
        copy_credential(args)
    elif args.command == "delete":
        delete_credential(args, metadata, metadata_path)
    elif args.command == "list":
        print_json(metadata)


if __name__ == "__main__":
    main()
