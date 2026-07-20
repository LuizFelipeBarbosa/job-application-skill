from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
DOCTOR = SKILL_ROOT / "scripts" / "doctor.py"


def load_doctor():
    spec = importlib.util.spec_from_file_location("apply_to_jobs_doctor", DOCTOR)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DoctorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.doctor = load_doctor()

    def test_validates_supported_integration_contract(self) -> None:
        self.doctor.validate_integrations(
            {
                "schema_version": 1,
                "email": {
                    "provider": "gmail",
                    "mode": "read_only_verification",
                    "allowed_operations": ["profile", "search", "read_selected_message"],
                    "prohibited_operations": [
                        "send", "draft", "archive", "delete", "label", "forward"
                    ],
                },
                "browser": {
                    "provider": "chrome",
                    "default_allowed_hosts": ["app.joinhandshake.com"],
                    "allow_all_sites": False,
                    "ats_approval": "one_time_per_verified_host",
                },
                "computer_use": {
                    "verification_only": True,
                    "full_support": ["darwin", "win32"],
                    "linux_support": "partial",
                    "diagnostic_route": "http://127.0.0.1:3000/diagnostics/browser",
                },
            }
        )

    def test_rejects_broad_browser_or_writable_email_access(self) -> None:
        invalid = {
            "schema_version": 1,
            "email": {"provider": "gmail", "mode": "full_access"},
            "browser": {
                "provider": "chrome",
                "default_allowed_hosts": [],
                "allow_all_sites": True,
            },
            "computer_use": {"verification_only": True},
        }
        with self.assertRaises(ValueError):
            self.doctor.validate_integrations(invalid)

    def test_reports_stable_schema_and_exit_codes(self) -> None:
        item = self.doctor.check("python", "pass", True, "supported")
        self.assertEqual(
            set(item), {"id", "status", "required", "message", "remediation"}
        )
        self.assertEqual(self.doctor.aggregate_status([item]), "pass")
        self.assertEqual(self.doctor.exit_code("pass", False), 0)
        self.assertEqual(self.doctor.exit_code("warn", False), 0)
        self.assertEqual(self.doctor.exit_code("fail", False), 1)
        self.assertEqual(self.doctor.exit_code("fail", True), 2)


if __name__ == "__main__":
    unittest.main()
