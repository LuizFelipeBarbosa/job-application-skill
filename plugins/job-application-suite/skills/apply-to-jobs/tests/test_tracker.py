from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILL_ROOT = Path(__file__).resolve().parents[1]
TRACKER = SKILL_ROOT / "scripts" / "tracker.py"


class TrackerCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.state_path = Path(self.temporary_directory.name) / "state.json"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def run_tracker(self, *arguments: str, succeeds: bool = True) -> dict | str:
        result = subprocess.run(
            [sys.executable, str(TRACKER), "--state", str(self.state_path), *arguments],
            text=True,
            capture_output=True,
            check=False,
        )
        if succeeds:
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        return result.stderr.strip()

    def start(self, target: int = 2) -> dict:
        return self.run_tracker(
            "start",
            "--target",
            str(target),
            "--objective",
            "Test application run",
        )

    def reserve_application(
        self,
        company: str,
        title: str,
        url: str,
        *,
        location: str = "",
        allow_possible_match: bool = False,
    ) -> dict:
        arguments = [
            "record",
            "--status",
            "in_progress",
            "--worker",
            "test-worker",
            "--company",
            company,
            "--title",
            title,
            "--url",
            url,
        ]
        if location:
            arguments.extend(("--location", location))
        if allow_possible_match:
            arguments.append("--allow-possible-match")
        return self.run_tracker(*arguments)

    def submit_application(
        self,
        application_id: str,
        company: str,
        title: str,
    ) -> dict:
        return self.run_tracker(
            "record",
            "--status",
            "submitted",
            "--application-id",
            application_id,
            "--company",
            company,
            "--title",
            title,
            "--confirmation",
            "Success page",
        )

    def test_blocked_application_updates_in_place_and_releases_slot(self) -> None:
        self.start()
        reserved = self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--worker",
            "worker-1",
            "--browser-session",
            "Acme role",
            "--company",
            "Acme",
            "--title",
            "Analyst",
            "--url",
            "https://jobs.example/acme-1",
        )
        application_id = reserved["recorded"]["id"]
        self.assertEqual(reserved["run"]["reserved"], 1)

        blocked = self.run_tracker(
            "record",
            "--status",
            "blocked",
            "--application-id",
            application_id,
            "--company",
            "Acme",
            "--title",
            "Analyst",
            "--reason-code",
            "candidate_answer",
            "--reason-category",
            "candidate_input",
            "--application-stage",
            "form_opened",
            "--note",
            "A required answer is unavailable.",
            "--browser-session",
            "Acme role",
            "--next-action",
            "Ask the candidate, then resume.",
        )
        self.assertEqual(blocked["run"]["blocked"], 1)
        self.assertEqual(blocked["run"]["reserved"], 0)
        self.assertEqual(blocked["run"]["available_slots"], 2)

        self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--application-id",
            application_id,
            "--worker",
            "worker-1",
            "--company",
            "Acme",
            "--title",
            "Analyst",
        )
        submitted = self.run_tracker(
            "record",
            "--status",
            "submitted",
            "--application-id",
            application_id,
            "--company",
            "Acme",
            "--title",
            "Analyst",
            "--confirmation",
            "Success page",
        )
        self.assertEqual(submitted["run"]["submitted"], 1)
        self.assertEqual(submitted["run"]["blocked"], 0)
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        self.assertEqual(len(state["runs"][0]["applications"]), 1)
        self.assertEqual(len(state["runs"][0]["applications"][0]["transitions"]), 4)

    def test_reserved_slot_prevents_an_unreserved_submission(self) -> None:
        self.start(target=1)
        first = self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--worker",
            "worker-1",
            "--company",
            "Acme",
            "--title",
            "Analyst",
            "--url",
            "https://jobs.example/acme-1",
        )
        error = self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--worker",
            "worker-2",
            "--company",
            "Beta",
            "--title",
            "Engineer",
            "--url",
            "https://jobs.example/beta-1",
            succeeds=False,
        )
        self.assertIn("No submission slot", error)

        self.run_tracker(
            "record",
            "--status",
            "blocked",
            "--application-id",
            first["recorded"]["id"],
            "--company",
            "Acme",
            "--title",
            "Analyst",
            "--reason-code",
            "verification",
            "--reason-category",
            "user_action",
            "--application-stage",
            "form_opened",
            "--note",
            "Verification is pending.",
            "--browser-session",
            "Acme role",
            "--next-action",
            "Complete verification.",
        )
        blocked_submit_error = self.run_tracker(
            "record",
            "--status",
            "submitted",
            "--application-id",
            first["recorded"]["id"],
            "--company",
            "Acme",
            "--title",
            "Analyst",
            "--confirmation",
            "Success page",
            succeeds=False,
        )
        self.assertIn("active reservation", blocked_submit_error)

        second = self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--worker",
            "worker-2",
            "--company",
            "Beta",
            "--title",
            "Engineer",
            "--url",
            "https://jobs.example/beta-1",
        )
        self.assertEqual(second["run"]["available_slots"], 0)

    def test_new_application_requires_an_exact_identifier(self) -> None:
        self.start()
        error = self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--worker",
            "worker-1",
            "--company",
            "Gamma",
            "--title",
            "Scientist",
            succeeds=False,
        )
        self.assertIn("non-empty URL", error)

    def test_exact_and_possible_duplicates_require_resolution(self) -> None:
        self.start()
        first = self.reserve_application(
            "Gamma", "Scientist", "https://jobs.example/gamma-1"
        )
        self.submit_application(first["recorded"]["id"], "Gamma", "Scientist")
        exact_error = self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--worker",
            "worker-2",
            "--company",
            "Gamma",
            "--title",
            "Scientist",
            "--url",
            "https://jobs.example/gamma-1",
            succeeds=False,
        )
        self.assertIn("already submitted", exact_error)

        possible_error = self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--worker",
            "worker-2",
            "--company",
            "Gamma",
            "--title",
            "Scientist",
            "--location",
            "Seattle, WA",
            "--url",
            "https://jobs.example/gamma-2",
            succeeds=False,
        )
        self.assertIn("possible prior submission", possible_error)

        distinct = self.reserve_application(
            "Gamma",
            "Scientist",
            "https://jobs.example/gamma-2",
            location="Seattle, WA",
            allow_possible_match=True,
        )
        submitted = self.submit_application(
            distinct["recorded"]["id"], "Gamma", "Scientist"
        )
        self.assertEqual(submitted["run"]["submitted"], 2)

    def test_completed_run_can_be_reopened_with_a_larger_target(self) -> None:
        self.start(target=1)
        application = self.reserve_application(
            "Delta", "Engineer", "https://jobs.example/delta-1"
        )
        self.submit_application(application["recorded"]["id"], "Delta", "Engineer")
        amended = self.run_tracker("amend", "--target", "2")
        self.assertTrue(amended["amended"])
        self.assertEqual(amended["status"], "active")
        self.assertEqual(amended["remaining"], 1)

    def test_possible_match_treats_missing_prior_location_as_unknown(self) -> None:
        self.start(target=1)
        application = self.reserve_application(
            "Epsilon", "Designer", "https://jobs.example/epsilon-1"
        )
        self.submit_application(
            application["recorded"]["id"], "Epsilon", "Designer"
        )
        result = self.run_tracker(
            "check",
            "--company",
            "Epsilon",
            "--title",
            "Designer",
            "--location",
            "Portland, OR",
            "--url",
            "https://jobs.example/epsilon-2",
        )
        self.assertIsNotNone(result["possible_match"])

    def test_prior_submission_is_rejected_before_reserving_browser_work(self) -> None:
        self.start(target=1)
        application = self.reserve_application(
            "Prior Co", "Engineer", "https://jobs.example/prior-1"
        )
        self.submit_application(
            application["recorded"]["id"], "Prior Co", "Engineer"
        )
        self.run_tracker("amend", "--target", "2")
        error = self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--worker",
            "worker-1",
            "--company",
            "Prior Co",
            "--title",
            "Engineer",
            "--url",
            "https://jobs.example/prior-1",
            succeeds=False,
        )
        self.assertIn("already submitted", error)

    def test_inferred_answers_require_evidence_references(self) -> None:
        self.start(target=1)
        error = self.run_tracker(
            "record",
            "--status",
            "in_progress",
            "--worker",
            "worker-1",
            "--company",
            "Zeta",
            "--title",
            "Researcher",
            "--url",
            "https://jobs.example/zeta-1",
            "--inferred-answer-count",
            "1",
            succeeds=False,
        )
        self.assertIn("--evidence-ref", error)

    def test_legacy_duplicate_events_are_collapsed_into_one_lifecycle(self) -> None:
        run_id = "legacy-run"
        legacy_state = {
            "schema_version": 1,
            "active_run_id": run_id,
            "runs": [
                {
                    "id": run_id,
                    "objective": "Legacy run",
                    "target": 2,
                    "status": "active",
                    "created_at": "2026-07-01T00:00:00+00:00",
                    "completed_at": None,
                    "applications": [
                        {
                            "id": "blocked-event",
                            "recorded_at": "2026-07-01T00:01:00+00:00",
                            "status": "blocked",
                            "site": "",
                            "company": "Legacy Co",
                            "title": "Analyst",
                            "location": "",
                            "url": "https://jobs.example/legacy-1",
                            "canonical_url": "https://jobs.example/legacy-1",
                            "job_id": "",
                            "confirmation": "",
                            "reason_code": "verification",
                            "note": "Waiting for verification.",
                        },
                        {
                            "id": "submitted-event",
                            "recorded_at": "2026-07-01T00:02:00+00:00",
                            "status": "submitted",
                            "site": "",
                            "company": "Legacy Co",
                            "title": "Analyst",
                            "location": "",
                            "url": "https://jobs.example/legacy-1",
                            "canonical_url": "https://jobs.example/legacy-1",
                            "job_id": "",
                            "confirmation": "Success page",
                            "reason_code": "",
                            "note": "",
                        },
                    ],
                }
            ],
        }
        self.state_path.write_text(json.dumps(legacy_state), encoding="utf-8")

        status = self.run_tracker("status")
        self.assertEqual(status["active_run"]["submitted"], 1)
        self.assertEqual(status["active_run"]["blocked"], 0)

        self.run_tracker("amend", "--objective", "Migrated legacy run")
        saved_state = json.loads(self.state_path.read_text(encoding="utf-8"))
        applications = saved_state["runs"][0]["applications"]
        self.assertEqual(len(applications), 1)
        self.assertEqual(len(applications[0]["transitions"]), 2)


if __name__ == "__main__":
    unittest.main()
