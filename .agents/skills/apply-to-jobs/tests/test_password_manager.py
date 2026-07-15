from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
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


class PasswordManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.password_manager, self.keyring = load_password_manager()

    def test_accepts_a_supported_os_backend(self) -> None:
        selected_backend = backend("keyring.backends.macOS")
        self.keyring.get_keyring = lambda: selected_backend
        returned_backend, backend_name = self.password_manager.secure_keyring_backend()
        self.assertIs(returned_backend, selected_backend)
        self.assertEqual(backend_name, "keyring.backends.macOS.Keyring")

    def test_rejects_an_unknown_positive_priority_backend(self) -> None:
        self.keyring.get_keyring = lambda: backend("third_party.encrypted_file")
        with self.assertRaisesRegex(SystemExit, "Unsupported credential backend"):
            self.password_manager.secure_keyring_backend()

    def test_delete_restores_the_secret_when_metadata_save_fails(self) -> None:
        self.keyring.get_keyring = lambda: backend("keyring.backends.macOS")
        credentials = {}

        def get_password(service: str, username: str) -> str | None:
            return credentials.get((service, username))

        def set_password(service: str, username: str, password: str) -> None:
            credentials[(service, username)] = password

        def delete_password(service: str, username: str) -> None:
            if credentials.pop((service, username), None) is None:
                raise PasswordDeleteError()

        self.keyring.get_password = get_password
        self.keyring.set_password = set_password
        self.keyring.delete_password = delete_password

        service = self.password_manager.credential_service("careers.example.com")
        credentials[(service, "candidate@example.com")] = "secret-value"
        metadata = {
            "schema_version": 1,
            "accounts": [
                {"site": "careers.example.com", "username": "candidate@example.com"}
            ],
        }
        args = argparse.Namespace(
            site="careers.example.com", username="candidate@example.com"
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            metadata_path = Path(temporary_directory) / "accounts.json"
            with mock.patch.object(
                self.password_manager,
                "save_metadata",
                side_effect=OSError("simulated write failure"),
            ):
                with self.assertRaisesRegex(SystemExit, "credential was restored"):
                    self.password_manager.delete_credential(
                        args, metadata, metadata_path
                    )

        self.assertEqual(
            credentials[(service, "candidate@example.com")], "secret-value"
        )
        self.assertEqual(len(metadata["accounts"]), 1)


if __name__ == "__main__":
    unittest.main()
