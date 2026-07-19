#!/usr/bin/env python3
"""Track bounded job-application runs without storing state in version control."""

from __future__ import annotations

import argparse
from copy import deepcopy
from collections.abc import Iterator
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from urllib.parse import urlsplit
from uuid import uuid4

from job_identity import (
    add_identity,
    build_identity,
    canonicalize_url,
    identity_key,
    identities_match,
    normalize_identities,
    normalize_text,
)


SCHEMA_VERSION = 1
SUCCESSFUL_APPLICATIONS_SCHEMA_VERSION = 1
RUN_KINDS = ("application", "recovery")
RECORD_STATUSES = (
    "in_progress",
    "blocked",
    "ready_to_submit",
    "submitted",
    "skipped",
)
REQUIRED_PREFLIGHT_CHECKS = {
    "identity",
    "posting_open",
    "timing",
    "work_authorization",
    "minimum_qualifications",
}
PREFLIGHT_RESULTS = {"pass", "fail", "unknown"}
PREFERENCE_RESULTS = {"match", "mismatch", "unknown"}
REASON_CATEGORIES = (
    "duplicate",
    "posting_unavailable",
    "eligibility",
    "hard_constraint",
    "safety",
    "target_reached",
    "technical",
    "candidate_input",
    "user_action",
    "policy",
    "employer_restriction",
    "other",
)
DECISION_STRENGTHS = ("hard", "soft", "unknown", "not_applicable")
APPLICATION_STAGES = (
    "unknown",
    "discovered",
    "preflight",
    "form_opened",
    "data_entered",
    "documents_uploaded",
    "ready_to_submit",
    "submission_attempted",
    "confirmed",
)
TRANSMITTED_DATA_TYPES = (
    "identity",
    "contact",
    "education",
    "employment",
    "documents",
    "screening_answers",
    "other",
)
VERIFICATION_TYPES = (
    "email_code",
    "captcha",
    "password",
    "account_recovery",
    "mfa",
    "passkey",
)
VERIFICATION_EVENTS = (
    "requested",
    "ready",
    "attempted",
    "succeeded",
    "failed",
    "expired",
    "user_action_required",
)
SECRET_ARGUMENT_PATTERN = re.compile(
    r"(?:password|passcode|otp|one.?time|secret|token|security.?code|verification.?code)",
    re.IGNORECASE,
)
RESERVED_STATUSES = {"in_progress", "ready_to_submit"}
ALLOWED_TRANSITIONS = {
    "in_progress": {
        "in_progress",
        "blocked",
        "ready_to_submit",
        "submitted",
        "skipped",
    },
    "blocked": {"in_progress", "blocked", "skipped"},
    "ready_to_submit": {
        "in_progress",
        "blocked",
        "ready_to_submit",
        "submitted",
        "skipped",
    },
    "skipped": {"skipped"},
    "submitted": {"submitted"},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def default_state_path() -> Path:
    current = Path.cwd().resolve()
    for directory in (current, *current.parents):
        if (directory / ".git").exists():
            return directory / "private" / "application-state.json"
    return current / "private" / "application-state.json"


def successful_applications_path(state_path: Path) -> Path:
    return state_path.with_name("successful-applications.json")


def transition_from_legacy_application(application: dict) -> dict:
    return {
        "at": application.get("recorded_at", utc_now()),
        "from": None,
        "to": application.get("status", "skipped"),
        "reason_code": application.get("reason_code", ""),
        "reason_category": application.get("reason_category", ""),
        "decision_strength": application.get("decision_strength", "unknown"),
        "application_stage": application.get("application_stage", "unknown"),
        "transmitted_data": application.get("transmitted_data", []),
        "note": application.get("note", ""),
        "worker": application.get("worker", ""),
        "browser_session": application.get("browser_session", ""),
        "next_action": application.get("next_action", ""),
    }


def normalize_application(application: dict) -> dict:
    normalized = dict(application)
    recorded_at = normalized.get("recorded_at", utc_now())
    normalized.setdefault("id", uuid4().hex)
    normalized.setdefault("recorded_at", recorded_at)
    normalized.setdefault("created_at", recorded_at)
    normalized.setdefault("updated_at", recorded_at)
    normalized.setdefault("site", "")
    normalized.setdefault("location", "")
    normalized.setdefault("url", "")
    normalized["identities"] = normalize_identities(normalized)
    primary_identity = normalized["identities"][-1] if normalized["identities"] else {}
    normalized["canonical_url"] = primary_identity.get(
        "canonical_url", canonicalize_url(normalized["url"])
    )
    normalized["job_id"] = normalized.get("job_id") or primary_identity.get("job_id", "")
    normalized["site_key"] = primary_identity.get("site_key", "")
    normalized.setdefault("confirmation", "")
    normalized.setdefault("reason_code", "")
    normalized.setdefault("reason_category", "")
    normalized.setdefault("decision_strength", "unknown")
    normalized.setdefault("application_stage", "unknown")
    normalized.setdefault("transmitted_data", [])
    normalized.setdefault("preflight_checks", {})
    normalized.setdefault("preference_checks", {})
    normalized.setdefault("note", "")
    normalized.setdefault("worker", "")
    normalized.setdefault("browser_session", "")
    normalized.setdefault("next_action", "")
    normalized.setdefault("profile_signature", "")
    normalized.setdefault("document_signatures", [])
    normalized.setdefault("evidence_refs", [])
    normalized.setdefault("inferred_answer_count", 0)
    normalized.setdefault("generated_answer_count", 0)
    normalized.setdefault("verification_type", "")
    normalized.setdefault("verification_events", [])
    normalized.setdefault("recovery_of", "")
    normalized.setdefault("resolved_by", "")
    normalized.setdefault("resolved_at", "")
    if not normalized.get("transitions"):
        normalized["transitions"] = [transition_from_legacy_application(normalized)]
    return normalized


def merge_application_lifecycle(current: dict, later: dict) -> None:
    current["transitions"].extend(later["transitions"])
    current["recorded_at"] = later["recorded_at"]
    current["updated_at"] = later["updated_at"]

    for field in (
        "status",
        "confirmation",
        "reason_code",
        "reason_category",
        "decision_strength",
        "application_stage",
        "transmitted_data",
        "preflight_checks",
        "preference_checks",
        "note",
        "next_action",
        "inferred_answer_count",
        "generated_answer_count",
    ):
        current[field] = later[field]
    for field in (
        "site",
        "company",
        "title",
        "location",
        "url",
        "canonical_url",
        "job_id",
        "worker",
        "browser_session",
        "profile_signature",
        "site_key",
        "recovery_of",
        "resolved_by",
        "resolved_at",
    ):
        if later.get(field):
            current[field] = later[field]
    for field in (
        "document_signatures",
        "evidence_refs",
        "verification_events",
    ):
        if later.get(field):
            current[field] = later[field]
    for identity in later.get("identities", []):
        add_identity(current["identities"], identity)


def normalize_state(state: dict) -> dict:
    """Upgrade append-only application events into one lifecycle per run and job."""
    for run in state["runs"]:
        run.setdefault("kind", "application")
        applications = []
        for raw_application in run.get("applications", []):
            application = normalize_application(raw_application)
            current = next(
                (
                    item
                    for item in applications
                    if exact_match(
                        item,
                        canonical_url=application["canonical_url"],
                        site=application["site"],
                        job_id=application["job_id"],
                    )
                ),
                None,
            )
            if current is None or (
                not application["canonical_url"]
                and not has_provider_identifier(
                    application["site"], application["job_id"]
                )
            ):
                applications.append(application)
            else:
                merge_application_lifecycle(current, application)
        run["applications"] = applications
    return state


def load_state(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": SCHEMA_VERSION, "active_run_id": None, "runs": []}

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Cannot read tracker state at {path}: {error}") from error

    if state.get("schema_version") != SCHEMA_VERSION or not isinstance(
        state.get("runs"), list
    ):
        raise SystemExit(f"Unsupported or invalid tracker state at {path}")
    return normalize_state(state)


def save_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as temporary_file:
            temporary_name = temporary_file.name
            json.dump(value, temporary_file, indent=2, sort_keys=True)
            temporary_file.write("\n")
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.unlink(temporary_name)


def save_state(path: Path, state: dict) -> None:
    save_json(path, state)


def save_successful_applications(path: Path, state: dict) -> None:
    applications = []
    for run in state["runs"]:
        for application in run["applications"]:
            if application["status"] != "submitted":
                continue
            applications.append(
                {
                    "run_id": run["id"],
                    "objective": run["objective"],
                    **application,
                }
            )

    save_json(
        path,
        {
            "schema_version": SUCCESSFUL_APPLICATIONS_SCHEMA_VERSION,
            "applications": applications,
        },
    )


def validate_url(value: str | None) -> str:
    url = (value or "").strip()
    if not url:
        return ""
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise SystemExit("Application URL must be an absolute HTTP or HTTPS URL.")
    return url


def has_provider_identifier(site: str | None, job_id: str | None) -> bool:
    return bool((site or "").strip() and (job_id or "").strip())


def get_active_run(state: dict, *, require_active: bool = False) -> dict | None:
    run_id = state.get("active_run_id")
    run = next((item for item in state["runs"] if item.get("id") == run_id), None)
    if run is not None and run.get("status") != "active":
        run = None
    if require_active and run is None:
        raise SystemExit(
            "No active application run. Start one before recording results."
        )
    return run


def run_summary(run: dict) -> dict:
    submitted = sum(item["status"] == "submitted" for item in run["applications"])
    reserved = sum(item["status"] in RESERVED_STATUSES for item in run["applications"])
    remaining = max(run["target"] - submitted, 0)
    return {
        "run_id": run["id"],
        "kind": run.get("kind", "application"),
        "status": run["status"],
        "objective": run["objective"],
        "target": run["target"],
        "submitted": submitted,
        "remaining": remaining,
        "reserved": reserved,
        "available_slots": max(remaining - reserved, 0),
        "in_progress": sum(
            item["status"] == "in_progress" for item in run["applications"]
        ),
        "ready_to_submit": sum(
            item["status"] == "ready_to_submit" for item in run["applications"]
        ),
        "blocked": sum(
            item["status"] == "blocked" and not item.get("resolved_by")
            for item in run["applications"]
        ),
        "skipped": sum(item["status"] == "skipped" for item in run["applications"]),
    }


def application_identity(application: dict) -> dict:
    return {
        "application_id": application["id"],
        "run_id": application["run_id"],
        "company": application["company"],
        "title": application["title"],
        "location": application.get("location", ""),
        "url": application.get("url", ""),
        "site": application.get("site", ""),
        "job_id": application.get("job_id", ""),
        "site_key": application.get("site_key", ""),
        "status": application.get("status", ""),
        "reason_category": application.get("reason_category", ""),
        "reason_code": application.get("reason_code", ""),
        "recorded_at": application["recorded_at"],
    }


def iter_submitted_applications(state: dict) -> Iterator[dict]:
    for run in state["runs"]:
        for application in run["applications"]:
            if application["status"] == "submitted":
                yield {"run_id": run["id"], **application}


def iter_applications(state: dict) -> Iterator[dict]:
    for run in state["runs"]:
        for application in run["applications"]:
            yield {"run_id": run["id"], **application}


def exact_match(
    application: dict,
    *,
    canonical_url: str,
    site: str | None,
    job_id: str | None,
) -> bool:
    requested = build_identity(site=site, url=canonical_url, job_id=job_id)
    return any(
        identities_match(identity, requested)
        for identity in normalize_identities(application)
    )


def find_exact_evaluations(
    state: dict,
    *,
    url: str | None,
    site: str | None,
    job_id: str | None,
) -> list[dict]:
    canonical_url = canonicalize_url(url)
    return [
        application_identity(application)
        for application in iter_applications(state)
        if exact_match(
            application,
            canonical_url=canonical_url,
            site=site,
            job_id=job_id,
        )
    ]


def find_prior_submission(
    state: dict,
    *,
    url: str | None,
    site: str | None,
    job_id: str | None,
) -> dict | None:
    return next(
        (
            application
            for application in find_exact_evaluations(
                state, url=url, site=site, job_id=job_id
            )
            if application["status"] == "submitted"
        ),
        None,
    )


def find_possible_submission(
    state: dict,
    *,
    company: str | None,
    title: str | None,
    location: str | None,
) -> dict | None:
    normalized_company = normalize_text(company)
    normalized_title = normalize_text(title)
    normalized_location = normalize_text(location)
    if not normalized_company or not normalized_title:
        return None

    for application in iter_submitted_applications(state):
        same_role = (
            normalize_text(application.get("company")) == normalized_company
            and normalize_text(application.get("title")) == normalized_title
        )
        prior_location = normalize_text(application.get("location"))
        same_or_unknown_location = (
            not normalized_location
            or not prior_location
            or prior_location == normalized_location
        )
        if same_role and same_or_unknown_location:
            return application_identity(application)
    return None


def find_run_application(
    run: dict,
    *,
    application_id: str | None,
    url: str | None,
    site: str | None,
    job_id: str | None,
) -> dict | None:
    requested_id = (application_id or "").strip()
    if requested_id:
        application = next(
            (item for item in run["applications"] if item.get("id") == requested_id),
            None,
        )
        if application is None:
            raise SystemExit(
                f"No application with ID {requested_id} exists in this run."
            )
        return application

    canonical_url = canonicalize_url(url)
    return next(
        (
            item
            for item in run["applications"]
            if exact_match(
                item,
                canonical_url=canonical_url,
                site=site,
                job_id=job_id,
            )
        ),
        None,
    )


def find_application_by_id(state: dict, application_id: str) -> dict | None:
    for run in state["runs"]:
        for application in run["applications"]:
            if application.get("id") == application_id:
                return application
    return None


def parse_timestamp(value: str, *, field_name: str) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise SystemExit(f"{field_name} must be an ISO-8601 timestamp.") from error
    if parsed.tzinfo is None:
        raise SystemExit(f"{field_name} must include a UTC offset.")
    return parsed.isoformat(timespec="seconds")


def print_json(value: dict) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def start_run(args: argparse.Namespace, state: dict, state_path: Path) -> None:
    objective = args.objective.strip()
    if not objective:
        raise SystemExit("Objective cannot be empty.")

    active_run = get_active_run(state)
    if active_run:
        same_run = (
            active_run["target"] == args.target
            and active_run.get("kind", "application") == args.kind
            and normalize_text(active_run["objective"]) == normalize_text(objective)
        )
        if not same_run:
            summary = run_summary(active_run)
            raise SystemExit(
                "An unfinished run already exists "
                f"({summary['submitted']}/{summary['target']} submitted). "
                "Resume it or use the amend command to change its target or objective."
            )
        print_json({"resumed": True, **run_summary(active_run)})
        return

    run = {
        "id": (
            f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-"
            f"{uuid4().hex[:8]}"
        ),
        "objective": objective,
        "kind": args.kind,
        "target": args.target,
        "status": "active",
        "created_at": utc_now(),
        "completed_at": None,
        "applications": [],
    }
    state["runs"].append(run)
    state["active_run_id"] = run["id"]
    save_state(state_path, state)
    print_json({"resumed": False, **run_summary(run)})


def show_status(state: dict) -> None:
    run = get_active_run(state)
    if run is not None:
        print_json({"active_run": run_summary(run)})
        return

    latest = run_summary(state["runs"][-1]) if state["runs"] else None
    print_json({"active_run": None, "latest_run": latest})


def check_submission(args: argparse.Namespace, state: dict) -> None:
    url = validate_url(args.url)
    has_exact_identifier = bool(url or has_provider_identifier(args.site, args.job_id))
    has_role_metadata = bool(args.company.strip() and args.title.strip())
    if not has_exact_identifier and not has_role_metadata:
        raise SystemExit(
            "Provide --url, both --site and --job-id, or both --company and --title."
        )
    prior = find_prior_submission(
        state, url=url, site=args.site, job_id=args.job_id
    )
    exact_evaluations = find_exact_evaluations(
        state, url=url, site=args.site, job_id=args.job_id
    )
    possible = None
    if prior is None:
        possible = find_possible_submission(
            state,
            company=args.company,
            title=args.title,
            location=args.location,
        )
    print_json(
        {
            "already_submitted": prior is not None,
            "match": prior,
            "exact_evaluations": exact_evaluations,
            "possible_match": possible,
        }
    )


def nonnegative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("count must not be negative")
    return number


def parse_named_results(
    values: list[str],
    *,
    allowed_results: set[str],
    flag_name: str,
) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        name, separator, result = value.partition("=")
        normalized_name = normalize_text(name).replace(" ", "_")
        normalized_result = normalize_text(result).replace(" ", "_")
        if not separator or not normalized_name or normalized_result not in allowed_results:
            choices = ", ".join(sorted(allowed_results))
            raise SystemExit(
                f"{flag_name} must use name=result with a result of: {choices}."
            )
        parsed[normalized_name] = normalized_result
    return parsed


def validate_reason_code(value: str) -> None:
    if value and not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*", value):
        raise SystemExit("--reason-code must be lower-case snake_case.")


def validate_record_request(
    args: argparse.Namespace,
    *,
    existing: dict | None,
    url: str,
) -> list[str]:
    warnings: list[str] = []
    if not args.company.strip() or not args.title.strip():
        raise SystemExit("Company and title must not be empty.")
    if existing is None and not (
        url or has_provider_identifier(args.site, args.job_id)
    ):
        raise SystemExit(
            "A new application requires a non-empty URL or both --site and --job-id."
        )
    if args.status == "submitted" and not args.confirmation.strip():
        raise SystemExit("A submitted application requires --confirmation evidence.")
    if args.status == "submitted" and (
        existing is None or existing.get("status") not in RESERVED_STATUSES
    ):
        raise SystemExit(
            "A submitted application must transition from an active reservation."
        )
    reason_code = args.reason_code.strip()
    validate_reason_code(reason_code)
    if args.status in {"blocked", "skipped"}:
        if not args.reason_category.strip() or not reason_code or not args.note.strip():
            raise SystemExit(
                f"A {args.status} application requires --reason-category, "
                "--reason-code, and --note."
            )
        if args.application_stage == "unknown":
            raise SystemExit(
                f"A {args.status} application requires a known --application-stage."
            )
    if args.status == "blocked":
        if not args.browser_session.strip() or not args.next_action.strip():
            raise SystemExit(
                "A blocked application requires --browser-session and --next-action."
            )
    if args.status == "skipped":
        if args.decision_strength in {"soft", "unknown"}:
            raise SystemExit(
                "A job cannot be skipped solely for a soft or unknown preference."
            )
        if args.reason_category != "target_reached" and not (
            args.evidence_ref or (existing or {}).get("evidence_refs")
        ):
            raise SystemExit("A skipped application requires at least one --evidence-ref.")
    if args.status == "in_progress" and not (
        args.worker.strip() or (existing and existing.get("worker"))
    ):
        raise SystemExit("An in-progress application requires --worker.")

    preflight_checks = parse_named_results(
        args.preflight_check,
        allowed_results=PREFLIGHT_RESULTS,
        flag_name="--preflight-check",
    ) or (existing or {}).get("preflight_checks", {})
    parse_named_results(
        args.preference_check,
        allowed_results=PREFERENCE_RESULTS,
        flag_name="--preference-check",
    )
    if args.status == "in_progress":
        missing = sorted(REQUIRED_PREFLIGHT_CHECKS - set(preflight_checks))
        if missing:
            warnings.append(
                "Reservation is missing preflight checks: " + ", ".join(missing)
            )
        failed = sorted(
            name for name, result in preflight_checks.items() if result == "fail"
        )
        if failed and not args.allow_hard_mismatch:
            raise SystemExit(
                "Hard preflight checks failed: "
                + ", ".join(failed)
                + ". Use --allow-hard-mismatch only after an explicit review."
            )
        if failed and args.allow_hard_mismatch and not (
            args.note.strip() and args.evidence_ref
        ):
            raise SystemExit(
                "A hard-mismatch override requires --note and --evidence-ref."
            )

    inferred_count = (
        args.inferred_answer_count
        if args.inferred_answer_count is not None
        else (existing or {}).get("inferred_answer_count", 0)
    )
    generated_count = (
        args.generated_answer_count
        if args.generated_answer_count is not None
        else (existing or {}).get("generated_answer_count", 0)
    )
    evidence_refs = args.evidence_ref or (existing or {}).get("evidence_refs", [])
    if (inferred_count or generated_count) and not evidence_refs:
        raise SystemExit(
            "Inferred or generated answers require at least one --evidence-ref."
        )
    return warnings


def validate_transition(existing: dict | None, args: argparse.Namespace) -> None:
    if existing is None:
        return
    current_status = existing["status"]
    if args.status in ALLOWED_TRANSITIONS.get(current_status, set()):
        return
    if current_status == "skipped" and args.reopen and args.status == "in_progress":
        return
    raise SystemExit(
        f"Cannot transition application from {current_status} to {args.status}."
    )


def validate_capacity(run: dict, existing: dict | None, requested_status: str) -> None:
    summary = run_summary(run)
    existing_reserved = bool(existing and existing["status"] in RESERVED_STATUSES)
    other_reserved = summary["reserved"] - int(existing_reserved)

    if requested_status in RESERVED_STATUSES:
        if summary["submitted"] + other_reserved >= run["target"]:
            raise SystemExit(
                "No submission slot is available. Resolve or release another "
                "reserved application."
            )
        return

    if requested_status == "submitted":
        projected_commitments = summary["submitted"] + other_reserved + 1
        if projected_commitments > run["target"]:
            raise SystemExit(
                "Submitting this application would exceed the run target or a "
                "reserved slot."
            )


def create_or_update_application(
    args: argparse.Namespace,
    *,
    run: dict,
    existing: dict | None,
    url: str,
) -> dict:
    now = utc_now()
    if existing is None:
        application = {
            "id": uuid4().hex,
            "created_at": now,
            "transitions": [],
        }
        run["applications"].append(application)
    else:
        application = existing
        application.setdefault("created_at", application.get("recorded_at", now))
        application.setdefault("transitions", [])

    previous_status = application.get("status")
    preflight_checks = dict(application.get("preflight_checks", {}))
    preflight_checks.update(
        parse_named_results(
            args.preflight_check,
            allowed_results=PREFLIGHT_RESULTS,
            flag_name="--preflight-check",
        )
    )
    preference_checks = dict(application.get("preference_checks", {}))
    preference_checks.update(
        parse_named_results(
            args.preference_check,
            allowed_results=PREFERENCE_RESULTS,
            flag_name="--preference-check",
        )
    )
    application_stage = (
        "confirmed"
        if args.status == "submitted"
        else args.application_stage or application.get("application_stage", "unknown")
    )
    reason_is_current = args.status in {"blocked", "skipped"}
    application.update(
        {
            "recorded_at": now,
            "updated_at": now,
            "status": args.status,
            "site": args.site.strip() or application.get("site", ""),
            "company": args.company.strip(),
            "title": args.title.strip(),
            "location": args.location.strip() or application.get("location", ""),
            "url": url or application.get("url", ""),
            "job_id": args.job_id.strip() or application.get("job_id", ""),
            "confirmation": args.confirmation.strip(),
            "reason_code": args.reason_code.strip() if reason_is_current else "",
            "reason_category": (
                args.reason_category.strip() if reason_is_current else ""
            ),
            "decision_strength": args.decision_strength,
            "application_stage": application_stage,
            "transmitted_data": args.transmitted_data
            or application.get("transmitted_data", []),
            "preflight_checks": preflight_checks,
            "preference_checks": preference_checks,
            "note": args.note.strip(),
            "worker": args.worker.strip() or application.get("worker", ""),
            "browser_session": args.browser_session.strip()
            or application.get("browser_session", ""),
            "next_action": args.next_action.strip() if args.status == "blocked" else "",
            "profile_signature": args.profile_signature.strip()
            or application.get("profile_signature", ""),
            "document_signatures": args.document_signature
            or application.get("document_signatures", []),
            "evidence_refs": args.evidence_ref or application.get("evidence_refs", []),
            "inferred_answer_count": (
                args.inferred_answer_count
                if args.inferred_answer_count is not None
                else application.get("inferred_answer_count", 0)
            ),
            "generated_answer_count": (
                args.generated_answer_count
                if args.generated_answer_count is not None
                else application.get("generated_answer_count", 0)
            ),
            "verification_type": args.verification_type
            or application.get("verification_type", ""),
        }
    )
    application.setdefault("identities", normalize_identities(application))
    new_identity = build_identity(
        site=application["site"],
        url=application["url"],
        job_id=application["job_id"],
    )
    add_identity(application["identities"], new_identity)
    application["canonical_url"] = new_identity["canonical_url"]
    application["job_id"] = new_identity["job_id"]
    application["site_key"] = new_identity["site_key"]
    application["transitions"].append(
        {
            "at": now,
            "from": previous_status,
            "to": args.status,
            "reason_code": application["reason_code"],
            "reason_category": application["reason_category"],
            "decision_strength": application["decision_strength"],
            "application_stage": application["application_stage"],
            "transmitted_data": application["transmitted_data"],
            "note": application["note"],
            "worker": application["worker"],
            "browser_session": application["browser_session"],
            "next_action": application["next_action"],
        }
    )
    return application


def record_application(
    args: argparse.Namespace,
    state: dict,
    state_path: Path,
    successful_applications_file: Path,
) -> None:
    run = get_active_run(state, require_active=True)
    assert run is not None

    url = validate_url(args.url)
    existing = find_run_application(
        run,
        application_id=args.application_id,
        url=url,
        site=args.site,
        job_id=args.job_id,
    )
    warnings = validate_record_request(args, existing=existing, url=url)

    identity_url = url or (existing or {}).get("url", "")
    identity_site = args.site or (existing or {}).get("site", "")
    identity_job_id = args.job_id or (existing or {}).get("job_id", "")
    prior = find_prior_submission(
        state,
        url=identity_url,
        site=identity_site,
        job_id=identity_job_id,
    )
    if prior is not None:
        raise SystemExit(
            "This role was already submitted: "
            f"{prior['company']} - {prior['title']} ({prior['recorded_at']})."
        )

    if existing is None:
        possible = find_possible_submission(
            state,
            company=args.company,
            title=args.title,
            location=args.location,
        )
        if possible is not None and not args.allow_possible_match:
            raise SystemExit(
                "A possible prior submission exists. Verify it, then rerun with "
                "--allow-possible-match only when this is a distinct role."
            )

    validate_transition(existing, args)
    validate_capacity(run, existing, args.status)

    application = create_or_update_application(
        args,
        run=run,
        existing=existing,
        url=url,
    )
    if application["status"] == "submitted" and application.get("recovery_of"):
        source = find_application_by_id(state, application["recovery_of"])
        if source is not None:
            source["resolved_by"] = application["id"]
            source["resolved_at"] = utc_now()
    summary = run_summary(run)
    if summary["remaining"] == 0:
        run["status"] = "complete"
        run["completed_at"] = utc_now()
        state["active_run_id"] = None
        summary = run_summary(run)

    save_state(state_path, state)
    save_successful_applications(successful_applications_file, state)
    print_json({"recorded": application, "run": summary, "warnings": warnings})


def recover_application(
    args: argparse.Namespace,
    state: dict,
    state_path: Path,
    successful_applications_file: Path,
) -> None:
    run = get_active_run(state, require_active=True)
    assert run is not None
    if run.get("kind", "application") != "recovery":
        raise SystemExit("Blocked applications require an active recovery run.")

    source = find_application_by_id(state, args.source_application_id.strip())
    if source is None:
        raise SystemExit("The blocked source application does not exist.")
    if source.get("status") != "blocked" or source.get("resolved_by"):
        raise SystemExit("Recovery requires an unresolved blocked application.")
    if any(
        application.get("recovery_of") == source["id"]
        for application in run["applications"]
    ):
        raise SystemExit("This blocked application is already in the recovery run.")

    prior = find_prior_submission(
        state,
        url=source.get("url"),
        site=source.get("site"),
        job_id=source.get("job_id"),
    )
    if prior is not None:
        raise SystemExit("This blocked role has already been submitted successfully.")

    preflight_checks = parse_named_results(
        args.preflight_check,
        allowed_results=PREFLIGHT_RESULTS,
        flag_name="--preflight-check",
    )
    for required in ("identity", "posting_open"):
        if preflight_checks.get(required) != "pass":
            raise SystemExit(
                f"Recovery requires --preflight-check {required}=pass."
            )
    failed = sorted(
        name for name, result in preflight_checks.items() if result == "fail"
    )
    if failed and not args.allow_hard_mismatch:
        raise SystemExit("Recovery preflight failed: " + ", ".join(failed))
    if failed and not (args.note.strip() and args.evidence_ref):
        raise SystemExit(
            "A recovery hard-mismatch override requires --note and --evidence-ref."
        )
    warnings = []
    missing = sorted(REQUIRED_PREFLIGHT_CHECKS - set(preflight_checks))
    if missing:
        warnings.append("Recovery preflight is missing: " + ", ".join(missing))

    validate_capacity(run, None, "in_progress")
    now = utc_now()
    application = normalize_application(
        {
            "id": uuid4().hex,
            "recorded_at": now,
            "created_at": now,
            "updated_at": now,
            "status": "in_progress",
            "site": source.get("site", ""),
            "company": source.get("company", ""),
            "title": source.get("title", ""),
            "location": source.get("location", ""),
            "url": source.get("url", ""),
            "job_id": source.get("job_id", ""),
            "identities": deepcopy(source.get("identities", [])),
            "worker": args.worker.strip(),
            "browser_session": args.browser_session.strip(),
            "note": args.note.strip(),
            "evidence_refs": args.evidence_ref
            or deepcopy(source.get("evidence_refs", [])),
            "preflight_checks": preflight_checks,
            "preference_checks": parse_named_results(
                args.preference_check,
                allowed_results=PREFERENCE_RESULTS,
                flag_name="--preference-check",
            ),
            "decision_strength": "not_applicable",
            "application_stage": "preflight",
            "recovery_of": source["id"],
            "transitions": [
                {
                    "at": now,
                    "from": None,
                    "to": "in_progress",
                    "reason_code": "",
                    "reason_category": "",
                    "decision_strength": "not_applicable",
                    "application_stage": "preflight",
                    "transmitted_data": [],
                    "note": args.note.strip(),
                    "worker": args.worker.strip(),
                    "browser_session": args.browser_session.strip(),
                    "next_action": "",
                }
            ],
        }
    )
    if not application["worker"] or not application["browser_session"]:
        raise SystemExit("Recovery requires --worker and --browser-session.")
    run["applications"].append(application)
    save_state(state_path, state)
    save_successful_applications(successful_applications_file, state)
    print_json(
        {"recovered": application, "run": run_summary(run), "warnings": warnings}
    )


def verification_event(
    args: argparse.Namespace,
    state: dict,
    state_path: Path,
) -> None:
    run = get_active_run(state, require_active=True)
    assert run is not None
    if run.get("kind", "application") != "recovery":
        raise SystemExit("Verification events require an active recovery run.")
    application = find_run_application(
        run,
        application_id=args.application_id,
        url=None,
        site=None,
        job_id=None,
    )
    assert application is not None
    if application.get("status") not in RESERVED_STATUSES:
        raise SystemExit("Verification requires an active recovery reservation.")

    verification_type = args.type
    browser_session = args.browser_session.strip()
    if not browser_session:
        raise SystemExit("Verification events require --browser-session.")
    lock = state.get("verification_lock")
    if lock and lock.get("application_id") != application["id"]:
        raise SystemExit(
            "Another application holds the serialized verification lock."
        )

    events = application.setdefault("verification_events", [])
    same_type_events = [
        event for event in events if event.get("type") == verification_type
    ]
    attempts = sum(event.get("event") == "attempted" for event in same_type_events)
    last_event = same_type_events[-1] if same_type_events else None
    now = utc_now()
    message_received_at = ""
    if args.message_received_at:
        message_received_at = parse_timestamp(
            args.message_received_at, field_name="--message-received-at"
        )

    if args.event == "requested":
        if last_event and last_event.get("event") not in {
            "failed",
            "expired",
            "user_action_required",
        }:
            raise SystemExit("A new verification request requires the prior flow to end.")
        state["verification_lock"] = {
            "application_id": application["id"],
            "type": verification_type,
            "browser_session": browser_session,
            "acquired_at": now,
        }
    else:
        if not lock or lock.get("application_id") != application["id"]:
            raise SystemExit("Request verification before recording this event.")
        if lock.get("browser_session") != browser_session:
            raise SystemExit("Verification must stay in the requesting browser session.")

    if verification_type == "email_code":
        if args.event == "ready":
            requested = next(
                (
                    event
                    for event in reversed(same_type_events)
                    if event.get("event") == "requested"
                ),
                None,
            )
            if requested is None or not message_received_at:
                raise SystemExit(
                    "Email-code readiness requires a request and "
                    "--message-received-at."
                )
            if datetime.fromisoformat(message_received_at) <= datetime.fromisoformat(
                requested["at"]
            ):
                raise SystemExit("The verification message predates the current request.")
        if args.event == "attempted":
            if not last_event or last_event.get("event") != "ready":
                raise SystemExit("Enter only a code marked ready for this session.")
            if attempts >= 2:
                raise SystemExit("Email-code verification allows only one clean retry.")
            attempts += 1
        if args.event in {"succeeded", "failed"} and (
            not last_event or last_event.get("event") != "attempted"
        ):
            raise SystemExit("Record a verification attempt before its result.")

    event = {
        "at": now,
        "type": verification_type,
        "event": args.event,
        "browser_session": browser_session,
        "attempt_number": attempts,
    }
    if message_received_at:
        event["message_received_at"] = message_received_at
    events.append(event)
    application["verification_type"] = verification_type
    application["updated_at"] = now

    terminal_event = args.event in {
        "succeeded",
        "expired",
        "user_action_required",
    }
    second_email_failure = (
        verification_type == "email_code" and args.event == "failed" and attempts >= 2
    )
    if second_email_failure:
        application.update(
            {
                "status": "blocked",
                "reason_category": "technical",
                "reason_code": "session_bound_code_rejected",
                "decision_strength": "not_applicable",
                "application_stage": "form_opened",
                "note": "Two session-bound email verification attempts were rejected.",
                "next_action": "Resume only after the provider resets verification.",
                "browser_session": browser_session,
            }
        )
        application.setdefault("transitions", []).append(
            {
                "at": now,
                "from": "in_progress",
                "to": "blocked",
                "reason_category": "technical",
                "reason_code": "session_bound_code_rejected",
                "decision_strength": "not_applicable",
                "application_stage": "form_opened",
                "transmitted_data": application.get("transmitted_data", []),
                "note": application["note"],
                "worker": application.get("worker", ""),
                "browser_session": browser_session,
                "next_action": application["next_action"],
            }
        )
        terminal_event = True
    if terminal_event:
        state.pop("verification_lock", None)

    save_state(state_path, state)
    print_json(
        {
            "recorded_event": event,
            "application_id": application["id"],
            "status": application["status"],
            "verification_locked": "verification_lock" in state,
        }
    )


def abandon_run(args: argparse.Namespace, state: dict, state_path: Path) -> None:
    run = get_active_run(state, require_active=True)
    assert run is not None
    run["status"] = "abandoned"
    run["completed_at"] = utc_now()
    run["abandon_reason"] = args.reason.strip()
    state["active_run_id"] = None
    save_state(state_path, state)
    print_json({"abandoned": True, **run_summary(run)})


def get_amendable_run(state: dict, run_id: str | None) -> dict:
    requested_id = (run_id or "").strip()
    if requested_id:
        run = next(
            (item for item in state["runs"] if item.get("id") == requested_id),
            None,
        )
        if run is None:
            raise SystemExit(f"No application run with ID {requested_id} exists.")
    else:
        run = get_active_run(state)
        if run is None:
            run = next(
                (
                    item
                    for item in reversed(state["runs"])
                    if item.get("status") == "complete"
                ),
                None,
            )
    if run is None:
        raise SystemExit(
            "No active or completed application run is available to amend."
        )
    if run.get("status") == "abandoned":
        raise SystemExit("An abandoned application run cannot be amended.")

    active_run = get_active_run(state)
    if active_run is not None and active_run["id"] != run["id"]:
        raise SystemExit(
            "Finish or abandon the active run before amending another run."
        )
    return run


def amend_run(args: argparse.Namespace, state: dict, state_path: Path) -> None:
    run = get_amendable_run(state, args.run_id)
    if args.target is None and args.objective is None:
        raise SystemExit("Provide --target, --objective, or both.")

    summary = run_summary(run)
    target = args.target if args.target is not None else run["target"]
    committed = summary["submitted"] + summary["reserved"]
    if target < summary["submitted"]:
        raise SystemExit(
            "Target cannot be lower than the "
            f"{summary['submitted']} confirmed submissions."
        )
    if target < committed:
        raise SystemExit(
            "Target cannot be lower than confirmed plus reserved applications. "
            "Release reserved applications first."
        )

    objective = (
        args.objective.strip() if args.objective is not None else run["objective"]
    )
    if not objective:
        raise SystemExit("Objective cannot be empty.")

    previous = {"target": run["target"], "objective": run["objective"]}
    changed = target != run["target"] or objective != run["objective"]
    if changed:
        amended_at = utc_now()
        run["target"] = target
        run["objective"] = objective
        run["amended_at"] = amended_at
        run.setdefault("amendments", []).append(
            {
                "amended_at": amended_at,
                "previous": previous,
                "updated": {"target": target, "objective": objective},
            }
        )
        if target == summary["submitted"]:
            run["status"] = "complete"
            run["completed_at"] = amended_at
            state["active_run_id"] = None
        else:
            run["status"] = "active"
            run["completed_at"] = None
            state["active_run_id"] = run["id"]
        save_state(state_path, state)

    print_json({"amended": changed, "previous": previous, **run_summary(run)})


def verification_type_for(application: dict) -> str:
    existing = application.get("verification_type", "")
    if existing in VERIFICATION_TYPES:
        return existing
    text = " ".join(
        (
            application.get("reason_code", ""),
            application.get("note", ""),
            application.get("next_action", ""),
        )
    ).lower()
    if re.search(r"verification code|security code|email verification|confirm.*email", text):
        return "email_code"
    if "captcha" in text:
        return "captcha"
    if "passkey" in text or "biometric" in text:
        return "passkey"
    if "account recovery" in text or "forgot password" in text:
        return "account_recovery"
    if "password" in text:
        return "password"
    if re.search(r"\bmfa\b|authenticator|device approval|security key", text):
        return "mfa"
    return ""


def build_review_report(state: dict) -> dict:
    applications = list(iter_applications(state))
    identity_groups: dict[tuple[str, str, str], list[dict]] = {}
    for application in applications:
        seen_keys = set()
        for identity in normalize_identities(application):
            key = identity_key(identity)
            if key in seen_keys or not (key[1] or key[2]):
                continue
            seen_keys.add(key)
            identity_groups.setdefault(key, []).append(application)

    repeated = []
    mixed = []
    for key, group in identity_groups.items():
        unique = {application["id"]: application for application in group}
        if len(unique) < 2:
            continue
        summary = {
            "site_key": key[0],
            "job_id": key[1],
            "canonical_url": key[2],
            "applications": [
                {
                    "application_id": application["id"],
                    "run_id": application["run_id"],
                    "status": application["status"],
                    "company": application.get("company", ""),
                    "title": application.get("title", ""),
                }
                for application in unique.values()
            ],
        }
        repeated.append(summary)
        if len({application["status"] for application in unique.values()}) > 1:
            mixed.append(summary)

    soft_pattern = re.compile(
        r"preferred|desired|no (?:numeric )?(?:salary|compensation)|"
        r"salary.*(?:unknown|not listed)|hard (?:minimum|floor)",
        re.IGNORECASE,
    )
    late_pattern = re.compile(
        r"transmitted partial|staged but|newly staged|resume.*(?:uploaded|transmitted)|"
        r"data (?:entered|transmitted)",
        re.IGNORECASE,
    )
    soft_skip_candidates = []
    late_preflight_candidates = []
    missing_metadata = []
    recoverable_blocked: dict[str, list[dict]] = {
        verification_type: [] for verification_type in VERIFICATION_TYPES
    }
    for application in applications:
        summary = {
            "application_id": application["id"],
            "run_id": application["run_id"],
            "company": application.get("company", ""),
            "title": application.get("title", ""),
            "status": application["status"],
        }
        missing = [
            field
            for field in (
                "site_key",
                "job_id",
                "reason_category",
                "reason_code",
                "application_stage",
            )
            if not application.get(field)
            and not (
                field in {"reason_category", "reason_code"}
                and application["status"] not in {"blocked", "skipped"}
            )
        ]
        if missing:
            missing_metadata.append({**summary, "missing": missing})
        note = application.get("note", "")
        if application["status"] == "skipped" and soft_pattern.search(note):
            soft_skip_candidates.append(
                {
                    **summary,
                    "reopen_argv": [
                        "record",
                        "--status",
                        "in_progress",
                        "--application-id",
                        application["id"],
                        "--reopen",
                    ],
                }
            )
        if application["status"] == "skipped" and late_pattern.search(note):
            late_preflight_candidates.append(summary)
        if application["status"] == "blocked" and not application.get("resolved_by"):
            verification_type = verification_type_for(application)
            if verification_type:
                recoverable_blocked[verification_type].append(
                    {
                        **summary,
                        "recover_argv": [
                            "recover",
                            "--source-application-id",
                            application["id"],
                        ],
                    }
                )

    return {
        "schema_version": 1,
        "generated_at": utc_now(),
        "repeated_identity_groups": repeated,
        "mixed_outcome_groups": mixed,
        "missing_structured_metadata": missing_metadata,
        "soft_skip_candidates": soft_skip_candidates,
        "late_preflight_candidates": late_preflight_candidates,
        "recoverable_blocked": recoverable_blocked,
    }


def backfill_tracker(
    args: argparse.Namespace,
    state: dict,
    state_path: Path,
    successful_applications_file: Path,
) -> None:
    raw_state = None
    if state_path.exists():
        raw_state = json.loads(state_path.read_text(encoding="utf-8"))
    raw_application_count = sum(
        len(run.get("applications", [])) for run in (raw_state or {}).get("runs", [])
    )
    normalized_application_count = sum(
        len(run.get("applications", [])) for run in state["runs"]
    )

    legacy_metadata_updates = 0
    for run in state["runs"]:
        for application in run["applications"]:
            application["identities"] = normalize_identities(application)
            if application["identities"]:
                primary = application["identities"][-1]
                application["site_key"] = primary["site_key"]
                application["job_id"] = primary["job_id"]
                application["canonical_url"] = primary["canonical_url"]
            if application["status"] in {"blocked", "skipped"}:
                if not application.get("reason_code"):
                    application["reason_code"] = "legacy_unclassified"
                    legacy_metadata_updates += 1
                if not application.get("reason_category"):
                    application["reason_category"] = "other"
                    legacy_metadata_updates += 1
            application.setdefault("decision_strength", "unknown")
            application.setdefault("application_stage", "unknown")
            application.setdefault("transmitted_data", [])
            application.setdefault("preflight_checks", {})
            application.setdefault("preference_checks", {})
            application.setdefault("verification_events", [])

    review = build_review_report(state)
    summary = {
        "dry_run": not args.apply,
        "raw_application_count": raw_application_count,
        "normalized_application_count": normalized_application_count,
        "collapsed_same_run_events": max(
            raw_application_count - normalized_application_count, 0
        ),
        "legacy_metadata_updates": legacy_metadata_updates,
        "repeated_identity_groups": len(review["repeated_identity_groups"]),
        "mixed_outcome_groups": len(review["mixed_outcome_groups"]),
        "soft_skip_candidates": len(review["soft_skip_candidates"]),
        "recoverable_blocked": sum(
            len(items) for items in review["recoverable_blocked"].values()
        ),
    }
    if not args.apply:
        print_json({"backfill": summary, "review": review})
        return

    if not state_path.exists():
        raise SystemExit("Cannot apply a backfill before the tracker exists.")
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = state_path.with_name(
        f"{state_path.stem}.{timestamp}.bak{state_path.suffix}"
    )
    shutil.copyfile(state_path, backup_path)
    os.chmod(backup_path, 0o600)
    save_state(state_path, state)
    save_successful_applications(successful_applications_file, state)
    review_path = (
        args.review_output.expanduser().resolve()
        if args.review_output
        else state_path.with_name("application-review.json")
    )
    save_json(review_path, review)
    print_json(
        {
            "backfill": summary,
            "backup_path": str(backup_path),
            "review_path": str(review_path),
        }
    )


def positive_integer(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("target must be a positive integer")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state",
        type=Path,
        default=None,
        help="Override the private state file path.",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start", help="Start or resume a bounded run.")
    start.add_argument("--target", required=True, type=positive_integer)
    start.add_argument("--objective", required=True)
    start.add_argument("--kind", choices=RUN_KINDS, default="application")

    commands.add_parser("status", help="Show progress for the current run.")

    check = commands.add_parser(
        "check", help="Check whether a job was submitted before."
    )
    check.add_argument("--url", default="")
    check.add_argument("--site", default="")
    check.add_argument("--job-id", default="")
    check.add_argument("--company", default="")
    check.add_argument("--title", default="")
    check.add_argument("--location", default="")

    record = commands.add_parser(
        "record", help="Create or update one application lifecycle."
    )
    record.add_argument("--status", required=True, choices=RECORD_STATUSES)
    record.add_argument("--application-id", default="")
    record.add_argument("--site", default="")
    record.add_argument("--company", required=True)
    record.add_argument("--title", required=True)
    record.add_argument("--location", default="")
    record.add_argument("--url", default="")
    record.add_argument("--job-id", default="")
    record.add_argument("--confirmation", default="")
    record.add_argument("--reason-code", default="")
    record.add_argument("--reason-category", choices=REASON_CATEGORIES, default="")
    record.add_argument(
        "--decision-strength", choices=DECISION_STRENGTHS, default="unknown"
    )
    record.add_argument(
        "--application-stage", choices=APPLICATION_STAGES, default="unknown"
    )
    record.add_argument(
        "--transmitted-data",
        action="append",
        choices=TRANSMITTED_DATA_TYPES,
        default=[],
    )
    record.add_argument("--preflight-check", action="append", default=[])
    record.add_argument("--preference-check", action="append", default=[])
    record.add_argument(
        "--verification-type", choices=VERIFICATION_TYPES, default=""
    )
    record.add_argument("--note", default="")
    record.add_argument("--worker", default="")
    record.add_argument("--browser-session", default="")
    record.add_argument("--next-action", default="")
    record.add_argument("--profile-signature", default="")
    record.add_argument("--document-signature", action="append", default=[])
    record.add_argument("--evidence-ref", action="append", default=[])
    record.add_argument("--inferred-answer-count", type=nonnegative_integer)
    record.add_argument("--generated-answer-count", type=nonnegative_integer)
    record.add_argument("--allow-possible-match", action="store_true")
    record.add_argument("--allow-hard-mismatch", action="store_true")
    record.add_argument("--reopen", action="store_true")

    recover = commands.add_parser(
        "recover", help="Reserve a blocked application in a recovery run."
    )
    recover.add_argument("--source-application-id", required=True)
    recover.add_argument("--worker", required=True)
    recover.add_argument("--browser-session", required=True)
    recover.add_argument("--preflight-check", action="append", default=[])
    recover.add_argument("--preference-check", action="append", default=[])
    recover.add_argument("--note", default="")
    recover.add_argument("--evidence-ref", action="append", default=[])
    recover.add_argument("--allow-hard-mismatch", action="store_true")

    verification = commands.add_parser(
        "verification-event",
        help="Record secret-free verification progress for a recovery.",
    )
    verification.add_argument("--application-id", required=True)
    verification.add_argument("--type", required=True, choices=VERIFICATION_TYPES)
    verification.add_argument("--event", required=True, choices=VERIFICATION_EVENTS)
    verification.add_argument("--browser-session", required=True)
    verification.add_argument("--message-received-at", default="")

    backfill = commands.add_parser(
        "backfill", help="Preview or apply identity and metadata backfill."
    )
    backfill.add_argument("--apply", action="store_true")
    backfill.add_argument("--review-output", type=Path)

    amend = commands.add_parser(
        "amend", help="Amend or reopen an active or completed run."
    )
    amend.add_argument("--run-id", default="")
    amend.add_argument("--target", type=positive_integer)
    amend.add_argument("--objective")

    abandon = commands.add_parser("abandon", help="Abandon the active run explicitly.")
    abandon.add_argument("--reason", required=True)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    state_path = (args.state or default_state_path()).expanduser().resolve()
    state = load_state(state_path)
    successful_applications_file = successful_applications_path(state_path)

    if args.command == "start":
        start_run(args, state, state_path)
        save_successful_applications(successful_applications_file, state)
    elif args.command == "status":
        show_status(state)
    elif args.command == "check":
        check_submission(args, state)
    elif args.command == "record":
        record_application(args, state, state_path, successful_applications_file)
    elif args.command == "recover":
        recover_application(args, state, state_path, successful_applications_file)
    elif args.command == "verification-event":
        verification_event(args, state, state_path)
    elif args.command == "backfill":
        backfill_tracker(args, state, state_path, successful_applications_file)
    elif args.command == "amend":
        amend_run(args, state, state_path)
        save_successful_applications(successful_applications_file, state)
    elif args.command == "abandon":
        abandon_run(args, state, state_path)
        save_successful_applications(successful_applications_file, state)


if __name__ == "__main__":
    main()
