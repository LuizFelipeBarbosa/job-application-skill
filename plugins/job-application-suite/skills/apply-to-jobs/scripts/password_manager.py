#!/usr/bin/env python3
"""Store job-site passwords in a supported operating-system credential vault."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import hmac
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
import time
from urllib.parse import urlsplit

try:
    import keyring
    from keyring.errors import KeyringError, PasswordDeleteError
except ImportError as error:
    raise SystemExit(
        "The local password manager requires the 'keyring' package. "
        "Run the repository bootstrap command before creating an account."
    ) from error


SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
SERVICE_PREFIX = "job-application-skill"
DEFAULT_PASSWORD_LENGTH = 24
DEFAULT_CLEAR_AFTER_SECONDS = 30
PASSWORD_SYMBOLS = "!@#$%^&*()-_=+"
AUTHORIZATION_MODES = {"bounded_run", "manual", "legacy_import"}
SUPPORTED_OS_BACKENDS = {
    "keyring.backends.macOS.Keyring",
    "keyring.backends.Windows.WinVaultKeyring",
    "keyring.backends.SecretService.Keyring",
    "keyring.backends.kwallet.DBusKeyring",
    "keyring.backends.kwallet.DBusKeyringKWallet4",
    "keyring.backends.libsecret.Keyring",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_metadata_path() -> Path:
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        if (directory / ".git").exists():
            return directory / "private" / "accounts.json"
    return current / "private" / "accounts.json"


def normalize_site(value: str) -> str:
    """Return a canonical host-only credential identifier."""
    site = value.strip()
    if not site:
        raise SystemExit("Site must not be empty.")
    if any(ord(character) < 32 for character in site):
        raise SystemExit("Site contains invalid characters.")

    parsed = urlsplit(site if "://" in site else f"//{site}")
    try:
        port = parsed.port
    except ValueError as error:
        raise SystemExit("Site contains an invalid port.") from error
    if not parsed.hostname or parsed.username or parsed.password or port is not None:
        raise SystemExit("Site must be a hostname or an HTTPS URL containing only a hostname.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise SystemExit("Site must not include a path, query, or fragment.")
    if "://" in site and parsed.scheme.lower() != "https":
        raise SystemExit("Site URLs must use HTTPS.")

    try:
        hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as error:
        raise SystemExit("Site contains an invalid internationalized hostname.") from error
    valid_labels = all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in hostname.split(".")
    )
    if not hostname or len(hostname) > 253 or not valid_labels:
        raise SystemExit("Site must contain a valid hostname.")
    return hostname


def credential_service(site: str) -> str:
    return f"{SERVICE_PREFIX}:{site}"


def normalize_username(value: str) -> str:
    username = value.strip()
    if not username:
        raise SystemExit("Username must not be empty.")
    if any(ord(character) < 32 for character in username):
        raise SystemExit("Username contains invalid characters.")
    return username


def empty_metadata() -> dict:
    return {"schema_version": SCHEMA_VERSION, "accounts": []}


def validate_timestamp(value: object, field: str, path: Path) -> None:
    if not isinstance(value, str):
        raise SystemExit(f"Invalid {field} timestamp in account metadata at {path}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise SystemExit(f"Invalid {field} timestamp in account metadata at {path}") from error
    if parsed.tzinfo is None:
        raise SystemExit(f"Invalid {field} timestamp in account metadata at {path}")


def validate_metadata(metadata: object, path: Path) -> dict:
    if not isinstance(metadata, dict):
        raise SystemExit(f"Unsupported or invalid account metadata at {path}")
    version = metadata.get("schema_version")
    accounts = metadata.get("accounts")
    if version not in {LEGACY_SCHEMA_VERSION, SCHEMA_VERSION} or not isinstance(accounts, list):
        raise SystemExit(f"Unsupported or invalid account metadata at {path}")

    for account in accounts:
        if not isinstance(account, dict):
            raise SystemExit(f"Unsupported or invalid account metadata at {path}")
        if not isinstance(account.get("site"), str) or not isinstance(account.get("username"), str):
            raise SystemExit(f"Unsupported or invalid account metadata at {path}")
        if version == SCHEMA_VERSION:
            if set(account) != {
                "site", "username", "created_at", "updated_at", "authorization"
            }:
                raise SystemExit(f"Unsupported or invalid account metadata at {path}")
            if normalize_site(account["site"]) != account["site"]:
                raise SystemExit(f"Account site is not canonical in metadata at {path}")
            if normalize_username(account["username"]) != account["username"]:
                raise SystemExit(f"Account username is not canonical in metadata at {path}")
            validate_timestamp(account.get("created_at"), "created_at", path)
            validate_timestamp(account.get("updated_at"), "updated_at", path)
            authorization = account.get("authorization")
            if (
                not isinstance(authorization, dict)
                or authorization.get("mode") not in AUTHORIZATION_MODES
                or not isinstance(authorization.get("confirmed_at"), str)
                or not isinstance(authorization.get("reference", ""), str)
                or set(authorization) != {"mode", "reference", "confirmed_at"}
            ):
                raise SystemExit(f"Unsupported or invalid account metadata at {path}")
            validate_timestamp(authorization["confirmed_at"], "confirmed_at", path)
            if authorization["mode"] == "bounded_run" and not authorization["reference"].strip():
                raise SystemExit(f"Bounded-run authorization has no reference at {path}")
    return metadata


def assert_private_permissions(path: Path) -> None:
    if os.name == "nt":
        return
    directory_mode = path.parent.stat().st_mode & 0o777
    file_mode = path.stat().st_mode & 0o777
    if directory_mode != 0o700 or file_mode != 0o600:
        raise SystemExit(
            f"Insecure account metadata permissions at {path}; require directory 0700 and file 0600."
        )


def load_metadata(path: Path) -> dict:
    if not path.exists():
        return empty_metadata()
    assert_private_permissions(path)
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Cannot read account metadata at {path}: {error}") from error
    return validate_metadata(metadata, path)


def harden_windows_path(path: Path, *, directory: bool) -> None:
    username = os.environ.get("USERNAME") or getpass.getuser()
    permission = f"{username}:(OI)(CI)F" if directory else f"{username}:F"
    result = subprocess.run(
        ["icacls", str(path), "/inheritance:r", "/grant:r", permission],
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise OSError(f"Cannot secure Windows permissions for {path}: {result.stderr.strip()}")


def ensure_private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == "nt":
        harden_windows_path(path, directory=True)
    else:
        os.chmod(path, 0o700)


def harden_private_file(path: Path) -> None:
    if os.name == "nt":
        harden_windows_path(path, directory=False)
    else:
        os.chmod(path, 0o600)


def save_metadata(path: Path, metadata: dict) -> None:
    validate_metadata(metadata, path)
    ensure_private_directory(path.parent)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary_file:
            temporary_name = temporary_file.name
            json.dump(metadata, temporary_file, indent=2, sort_keys=True)
            temporary_file.write("\n")
        harden_private_file(Path(temporary_name))
        os.replace(temporary_name, path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def migrate_metadata(metadata: dict) -> tuple[dict, list[str]]:
    if metadata["schema_version"] == SCHEMA_VERSION:
        return metadata, []

    migrated_accounts = []
    seen_identities: set[tuple[str, str]] = set()
    collisions = []
    for account in metadata["accounts"]:
        site = normalize_site(account["site"])
        username = normalize_username(account["username"])
        identity = (site, username)
        if identity in seen_identities:
            collisions.append(f"{site}|{username}")
            continue
        seen_identities.add(identity)
        confirmed_at = (
            account.get("permission_confirmed_at")
            or account.get("updated_at")
            or account.get("created_at")
            or utc_now()
        )
        migrated_accounts.append(
            {
                "site": site,
                "username": username,
                "created_at": account.get("created_at", confirmed_at),
                "updated_at": account.get("updated_at", confirmed_at),
                "authorization": {
                    "mode": "legacy_import",
                    "reference": "schema-v1",
                    "confirmed_at": confirmed_at,
                },
            }
        )
    return {"schema_version": SCHEMA_VERSION, "accounts": migrated_accounts}, collisions


def migration_backup_path(path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return path.with_name(f"{path.name}.backup-{timestamp}")


def secure_keyring_backend():
    backend = keyring.get_keyring()
    backend_name = f"{backend.__class__.__module__}.{backend.__class__.__name__}"
    try:
        priority = backend.priority
    except (AttributeError, RuntimeError) as error:
        raise SystemExit(f"Cannot initialize a secure credential vault: {error}") from error

    if priority <= 0 or backend_name not in SUPPORTED_OS_BACKENDS:
        raise SystemExit(
            f"Unsupported credential backend: {backend_name}. Configure a supported "
            "operating-system vault; chained, plaintext, and third-party file backends "
            "are not allowed."
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


def clipboard_commands(*, read: bool) -> list[tuple[list[str], str]]:
    if sys.platform == "darwin":
        return [(["pbpaste"] if read else ["pbcopy"], "pbpaste" if read else "pbcopy")]
    if os.name == "nt":
        if read:
            return [
                (
                    ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", "Get-Clipboard -Raw"],
                    "powershell.exe",
                )
            ]
        return [(["clip.exe"], "clip.exe")]
    if read:
        return [
            (["wl-paste", "--no-newline"], "wl-paste"),
            (["xclip", "-selection", "clipboard", "-o"], "xclip"),
            (["xsel", "--clipboard", "--output"], "xsel"),
        ]
    return [
        (["wl-copy"], "wl-copy"),
        (["xclip", "-selection", "clipboard"], "xclip"),
        (["xsel", "--clipboard", "--input"], "xsel"),
    ]


def copy_to_clipboard(value: str) -> None:
    for command, executable in clipboard_commands(read=False):
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


def read_clipboard() -> str:
    for command, executable in clipboard_commands(read=True):
        if shutil.which(executable):
            try:
                result = subprocess.run(
                    command,
                    text=True,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except subprocess.CalledProcessError as error:
                raise SystemExit(f"Clipboard command failed: {executable}") from error
            return result.stdout
    raise SystemExit("No supported local clipboard read command is available.")


def guard_clipboard(expected_sha256: str, delay_seconds: int) -> None:
    time.sleep(delay_seconds)
    current_digest = hashlib.sha256(read_clipboard().encode("utf-8")).hexdigest()
    if hmac.compare_digest(current_digest, expected_sha256):
        copy_to_clipboard("")


def start_clipboard_guard(password: str, delay_seconds: int) -> None:
    expected_digest = hashlib.sha256(password.encode("utf-8")).hexdigest()
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "_guard-clipboard",
        "--expected-sha256",
        expected_digest,
        "--delay",
        str(delay_seconds),
    ]
    options: dict = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        options["creationflags"] = (
            getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    else:
        options["start_new_session"] = True
    try:
        subprocess.Popen(command, **options)
    except OSError as error:
        try:
            copy_to_clipboard("")
        except SystemExit:
            pass
        raise SystemExit("Cannot start the guarded clipboard clear; the clipboard was cleared.") from error


def print_json(value: dict) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def require_current_schema(metadata: dict) -> None:
    if metadata["schema_version"] != SCHEMA_VERSION:
        raise SystemExit(
            "Account metadata uses schema v1. Preview 'migrate-metadata', then run "
            "'migrate-metadata --apply' before changing credentials."
        )


def authorization_from_args(args: argparse.Namespace) -> dict:
    reference = args.authorization_reference.strip()
    if args.authorization_mode == "bounded_run" and not reference:
        raise SystemExit("--authorization-reference is required for bounded-run authorization.")
    return {
        "mode": args.authorization_mode,
        "reference": reference or "manual-cli",
        "confirmed_at": utc_now(),
    }


def generate_credential(args: argparse.Namespace, metadata: dict, metadata_path: Path) -> None:
    require_current_schema(metadata)
    _, backend_name = secure_keyring_backend()
    site = normalize_site(args.site)
    username = normalize_username(args.username)
    authorization = authorization_from_args(args)

    service = credential_service(site)
    try:
        previous_password = keyring.get_password(service, username)
    except KeyringError as error:
        raise SystemExit(f"Cannot read from the credential vault: {error}") from error
    if previous_password is not None:
        raise SystemExit("A password already exists for this site and username.")

    password = generate_password(args.length, include_symbols=not args.no_symbols)
    try:
        keyring.set_password(service, username, password)
    except KeyringError as error:
        raise SystemExit(f"Cannot write to the credential vault: {error}") from error

    now = utc_now()
    account = find_account(metadata, site, username)
    if account is None:
        metadata["accounts"].append(
            {
                "site": site,
                "username": username,
                "created_at": now,
                "updated_at": now,
                "authorization": authorization,
            }
        )
    else:
        account["updated_at"] = now
        account["authorization"] = authorization

    try:
        save_metadata(metadata_path, metadata)
    except OSError as error:
        try:
            keyring.delete_password(service, username)
        except KeyringError as rollback_error:
            raise SystemExit(
                "CRITICAL: account metadata could not be saved and the new vault "
                "credential could not be removed. Reconcile the credential manually."
            ) from rollback_error
        raise SystemExit("Cannot save private account metadata; the new credential was removed.") from error

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
    if args.clear_after < 0 or args.clear_after > 300:
        raise SystemExit("--clear-after must be between 0 and 300 seconds.")
    try:
        password = keyring.get_password(credential_service(site), username)
    except KeyringError as error:
        raise SystemExit(f"Cannot read from the credential vault: {error}") from error
    if password is None:
        raise SystemExit("No password exists for this site and username.")

    copy_to_clipboard(password)
    if args.clear_after:
        start_clipboard_guard(password, args.clear_after)
    print_json(
        {
            "copied": True,
            "site": site,
            "username": username,
            "clear_after_seconds": args.clear_after,
            "password_printed": False,
        }
    )


def delete_credential(args: argparse.Namespace, metadata: dict, metadata_path: Path) -> None:
    require_current_schema(metadata)
    secure_keyring_backend()
    site = normalize_site(args.site)
    username = normalize_username(args.username)
    service = credential_service(site)
    try:
        previous_password = keyring.get_password(service, username)
    except KeyringError as error:
        raise SystemExit(f"Cannot read from the credential vault: {error}") from error
    if previous_password is None:
        raise SystemExit("No password exists for this site and username.")

    try:
        keyring.delete_password(service, username)
    except PasswordDeleteError as error:
        raise SystemExit("No password exists for this site and username.") from error
    except KeyringError as error:
        raise SystemExit(f"Cannot delete from the credential vault: {error}") from error

    updated_metadata = {
        **metadata,
        "accounts": [
            account
            for account in metadata["accounts"]
            if not (account.get("site") == site and account.get("username") == username)
        ],
    }
    try:
        save_metadata(metadata_path, updated_metadata)
    except OSError as error:
        try:
            keyring.set_password(service, username, previous_password)
        except KeyringError as rollback_error:
            raise SystemExit(
                "CRITICAL: account metadata could not be saved and the deleted vault "
                "credential could not be restored. Recreate it before continuing."
            ) from rollback_error
        raise SystemExit("Cannot save private account metadata; the credential was restored.") from error
    print_json({"deleted": True, "site": site, "username": username})


def migrate_metadata_command(args: argparse.Namespace, metadata: dict, path: Path) -> None:
    migrated, collisions = migrate_metadata(metadata)
    result = {
        "migration_required": metadata["schema_version"] != SCHEMA_VERSION,
        "from_schema_version": metadata["schema_version"],
        "to_schema_version": SCHEMA_VERSION,
        "account_count": len(migrated["accounts"]),
        "collisions": collisions,
        "applied": False,
    }
    if collisions:
        result["message"] = "Resolve canonical site and username collisions before applying."
        print_json(result)
        if args.apply:
            raise SystemExit("Metadata migration was not applied because identities collide.")
        return
    if args.apply and result["migration_required"]:
        validate_metadata(migrated, path)
        ensure_private_directory(path.parent)
        backup = migration_backup_path(path)
        try:
            shutil.copy2(path, backup)
            try:
                harden_private_file(backup)
            except OSError:
                backup.unlink(missing_ok=True)
                raise
            save_metadata(path, migrated)
        except OSError as error:
            raise SystemExit(
                "Metadata migration was not applied; the original metadata remains in place."
            ) from error
        result["applied"] = True
        result["backup"] = str(backup)
    print_json(result)


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
    generate.add_argument(
        "--authorization-mode", choices=("bounded_run", "manual"), required=True
    )
    generate.add_argument("--authorization-reference", default="")

    copy = commands.add_parser("copy", help="Copy a stored password without printing it.")
    copy.add_argument("--site", required=True)
    copy.add_argument("--username", required=True)
    copy.add_argument("--clear-after", type=int, default=DEFAULT_CLEAR_AFTER_SECONDS)

    delete = commands.add_parser("delete", help="Delete a stored password and its metadata.")
    delete.add_argument("--site", required=True)
    delete.add_argument("--username", required=True)

    migration = commands.add_parser(
        "migrate-metadata", help="Preview or apply the account metadata v2 migration."
    )
    migration.add_argument("--apply", action="store_true")

    guard = commands.add_parser("_guard-clipboard", help=argparse.SUPPRESS)
    guard.add_argument("--expected-sha256", required=True)
    guard.add_argument("--delay", type=int, required=True)

    commands.add_parser("clear-clipboard", help="Remove the copied password from the clipboard.")
    commands.add_parser("backend", help="Show the active secure credential-vault backend.")
    commands.add_parser("list", help="List non-secret account metadata.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    metadata_path = (args.metadata or default_metadata_path()).expanduser().resolve()

    if args.command == "_guard-clipboard":
        guard_clipboard(args.expected_sha256, args.delay)
        return
    if args.command == "clear-clipboard":
        copy_to_clipboard("")
        print_json({"clipboard_cleared": True})
        return
    if args.command == "backend":
        _, backend_name = secure_keyring_backend()
        print_json({"backend": backend_name, "secure": True})
        return
    if args.command == "copy":
        copy_credential(args)
        return

    metadata = load_metadata(metadata_path)
    if args.command == "generate":
        generate_credential(args, metadata, metadata_path)
    elif args.command == "delete":
        delete_credential(args, metadata, metadata_path)
    elif args.command == "migrate-metadata":
        migrate_metadata_command(args, metadata, metadata_path)
    elif args.command == "list":
        print_json(metadata)


if __name__ == "__main__":
    main()
