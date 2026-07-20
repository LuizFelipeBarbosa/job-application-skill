from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import types
import unittest
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]
PASSWORD_MANAGER = SKILL_ROOT / "scripts" / "password_manager.py"


class KeyringError(Exception):
    pass


class PasswordDeleteError(KeyringError):
    pass


def load_password_manager():
    keyring_module = types.ModuleType("keyring")
    errors_module = types.ModuleType("keyring.errors")
    errors_module.KeyringError = KeyringError
    errors_module.PasswordDeleteError = PasswordDeleteError
    keyring_module.errors = errors_module
    with mock.patch.dict(
        sys.modules,
        {"keyring": keyring_module, "keyring.errors": errors_module},
    ):
        spec = importlib.util.spec_from_file_location(
            "apply_to_jobs_password_manager", PASSWORD_MANAGER
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return module, keyring_module


def backend(module_name: str):
    backend_type = type("Keyring", (), {"priority": 5})
    backend_type.__module__ = module_name
    return backend_type()


def metadata_v2() -> dict:
    return {"schema_version": 2, "accounts": []}


class PasswordManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.password_manager, self.keyring = load_password_manager()

    def use_memory_keyring(self) -> dict:
        self.keyring.get_keyring = lambda: backend("keyring.backends.macOS")
        credentials = {}
        self.keyring.get_password = lambda service, username: credentials.get((service, username))
        self.keyring.set_password = (
            lambda service, username, password: credentials.__setitem__((service, username), password)
        )

        def delete_password(service: str, username: str) -> None:
            if credentials.pop((service, username), None) is None:
                raise PasswordDeleteError()

        self.keyring.delete_password = delete_password
        return credentials

    def test_accepts_supported_backend_and_rejects_unknown_backend(self) -> None:
        selected_backend = backend("keyring.backends.macOS")
        self.keyring.get_keyring = lambda: selected_backend
        returned_backend, backend_name = self.password_manager.secure_keyring_backend()
        self.assertIs(returned_backend, selected_backend)
        self.assertEqual(backend_name, "keyring.backends.macOS.Keyring")

        self.keyring.get_keyring = lambda: backend("third_party.encrypted_file")
        with self.assertRaisesRegex(SystemExit, "Unsupported credential backend"):
            self.password_manager.secure_keyring_backend()

    def test_normalizes_host_only_sites_and_rejects_paths_or_insecure_urls(self) -> None:
        self.assertEqual(
            self.password_manager.normalize_site("https://EXAMPLE.com/"), "example.com"
        )
        self.assertEqual(
            self.password_manager.normalize_site("https://bücher.example"),
            "xn--bcher-kva.example",
        )
        for value in (
            "https://example.com/register",
            "http://example.com",
            "example.com/jobs",
            "https://example.com:8443",
        ):
            with self.subTest(value=value):
                with self.assertRaises(SystemExit):
                    self.password_manager.normalize_site(value)

    def test_password_generation_meets_policy(self) -> None:
        password = self.password_manager.generate_password(24, include_symbols=True)
        self.assertEqual(len(password), 24)
        self.assertTrue(any(value.islower() for value in password))
        self.assertTrue(any(value.isupper() for value in password))
        self.assertTrue(any(value.isdigit() for value in password))
        self.assertTrue(any(value in self.password_manager.PASSWORD_SYMBOLS for value in password))
        with self.assertRaisesRegex(SystemExit, "at least 16"):
            self.password_manager.generate_password(15, include_symbols=True)

    def test_migrates_v1_metadata_without_claiming_new_authorization(self) -> None:
        legacy = {
            "schema_version": 1,
            "accounts": [
                {
                    "site": "HTTPS://Careers.Example.com/",
                    "username": "candidate@example.com",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "permission_confirmed_at": "2026-01-02T00:00:00+00:00",
                }
            ],
        }
        migrated, collisions = self.password_manager.migrate_metadata(legacy)
        self.assertEqual(collisions, [])
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["accounts"][0]["site"], "careers.example.com")
        self.assertEqual(
            migrated["accounts"][0]["authorization"],
            {
                "mode": "legacy_import",
                "reference": "schema-v1",
                "confirmed_at": "2026-01-02T00:00:00+00:00",
            },
        )

    def test_applied_migration_creates_private_timestamped_backup(self) -> None:
        legacy = {
            "schema_version": 1,
            "accounts": [
                {
                    "site": "careers.example.com",
                    "username": "candidate@example.com",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "permission_confirmed_at": "2026-01-02T00:00:00+00:00",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary_directory:
            private = Path(temporary_directory) / "private"
            private.mkdir(mode=0o700)
            path = private / "accounts.json"
            path.write_text(json.dumps(legacy), encoding="utf-8")
            os.chmod(path, 0o600)
            with redirect_stdout(io.StringIO()):
                self.password_manager.migrate_metadata_command(
                    argparse.Namespace(apply=True), legacy, path
                )
            backups = list(private.glob("accounts.json.backup-*"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode), 0o600)
            self.assertEqual(json.loads(path.read_text())["schema_version"], 2)

    def test_save_metadata_enforces_private_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            private = Path(temporary_directory) / "private"
            path = private / "accounts.json"
            self.password_manager.save_metadata(path, metadata_v2())
            self.assertEqual(stat.S_IMODE(private.stat().st_mode), 0o700)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

            if os.name != "nt":
                os.chmod(path, 0o644)
                with self.assertRaisesRegex(SystemExit, "Insecure account metadata permissions"):
                    self.password_manager.load_metadata(path)

    def test_generate_records_bounded_run_authorization(self) -> None:
        credentials = self.use_memory_keyring()
        args = argparse.Namespace(
            site="careers.example.com",
            username="candidate@example.com",
            length=24,
            no_symbols=False,
            authorization_mode="bounded_run",
            authorization_reference="run-123",
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "private" / "accounts.json"
            with redirect_stdout(io.StringIO()):
                self.password_manager.generate_credential(args, metadata_v2(), path)
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored["accounts"][0]["authorization"]["mode"], "bounded_run")
        self.assertEqual(stored["accounts"][0]["authorization"]["reference"], "run-123")
        service = self.password_manager.credential_service("careers.example.com")
        self.assertIn((service, "candidate@example.com"), credentials)

    def test_generate_reports_critical_rollback_failure(self) -> None:
        self.use_memory_keyring()
        self.keyring.delete_password = mock.Mock(side_effect=KeyringError("denied"))
        args = argparse.Namespace(
            site="careers.example.com",
            username="candidate@example.com",
            length=24,
            no_symbols=False,
            authorization_mode="manual",
            authorization_reference="",
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "accounts.json"
            with mock.patch.object(
                self.password_manager, "save_metadata", side_effect=OSError("write failure")
            ):
                with self.assertRaisesRegex(SystemExit, "CRITICAL"):
                    self.password_manager.generate_credential(args, metadata_v2(), path)

    def test_delete_restores_secret_when_metadata_save_fails(self) -> None:
        credentials = self.use_memory_keyring()
        service = self.password_manager.credential_service("careers.example.com")
        credentials[(service, "candidate@example.com")] = "secret-value"
        metadata = metadata_v2()
        metadata["accounts"].append(
            {
                "site": "careers.example.com",
                "username": "candidate@example.com",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "authorization": {
                    "mode": "manual",
                    "reference": "manual-cli",
                    "confirmed_at": "2026-01-01T00:00:00+00:00",
                },
            }
        )
        args = argparse.Namespace(site="careers.example.com", username="candidate@example.com")
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "accounts.json"
            with mock.patch.object(
                self.password_manager, "save_metadata", side_effect=OSError("write failure")
            ):
                with self.assertRaisesRegex(SystemExit, "credential was restored"):
                    self.password_manager.delete_credential(args, metadata, path)
        self.assertEqual(credentials[(service, "candidate@example.com")], "secret-value")

    def test_guard_clears_only_unchanged_clipboard(self) -> None:
        secret = "secret-value"
        digest = self.password_manager.hashlib.sha256(secret.encode()).hexdigest()
        with mock.patch.object(self.password_manager.time, "sleep"), mock.patch.object(
            self.password_manager, "read_clipboard", return_value=secret
        ), mock.patch.object(self.password_manager, "copy_to_clipboard") as clear:
            self.password_manager.guard_clipboard(digest, 30)
            clear.assert_called_once_with("")

        with mock.patch.object(self.password_manager.time, "sleep"), mock.patch.object(
            self.password_manager, "read_clipboard", return_value="new clipboard value"
        ), mock.patch.object(self.password_manager, "copy_to_clipboard") as clear:
            self.password_manager.guard_clipboard(digest, 30)
            clear.assert_not_called()

    def test_guard_process_receives_only_a_digest(self) -> None:
        with mock.patch.object(self.password_manager.subprocess, "Popen") as popen:
            self.password_manager.start_clipboard_guard("secret-value", 30)
        arguments = popen.call_args.args[0]
        self.assertNotIn("secret-value", arguments)
        self.assertIn("--expected-sha256", arguments)

    def test_guard_start_failure_clears_clipboard_and_fails(self) -> None:
        with mock.patch.object(
            self.password_manager.subprocess, "Popen", side_effect=OSError("blocked")
        ), mock.patch.object(self.password_manager, "copy_to_clipboard") as clear:
            with self.assertRaisesRegex(SystemExit, "guarded clipboard clear"):
                self.password_manager.start_clipboard_guard("secret-value", 30)
        clear.assert_called_once_with("")

    def test_public_cli_does_not_offer_replace(self) -> None:
        parser = self.password_manager.build_parser()
        subparsers = next(
            action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
        )
        generate_parser = subparsers.choices["generate"]
        option_strings = {
            option
            for action in generate_parser._actions
            for option in action.option_strings
        }
        self.assertNotIn("--replace", option_strings)


if __name__ == "__main__":
    unittest.main()
