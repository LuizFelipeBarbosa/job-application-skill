#!/usr/bin/env python3
"""Track bounded job-application runs without storing state in version control."""

from __future__ import annotations

import argparse
from collections.abc import Iterator
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4


SCHEMA_VERSION = 1
SUCCESSFUL_APPLICATIONS_SCHEMA_VERSION = 1
TRACKING_QUERY_KEYS = {
    "gh_src",
    "lever-source",
    "ref",
    "source",
    "sourceid",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}
RECORD_STATUSES = (
    "in_progress",
    "blocked",
    "ready_to_submit",
    "submitted",
    "skipped",
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
    if not normalized.get("canonical_url"):
        normalized["canonical_url"] = canonicalize_url(normalized["url"])
    normalized.setdefault("job_id", "")
    normalized.setdefault("confirmation", "")
    normalized.setdefault("reason_code", "")
    normalized.setdefault("note", "")
    normalized.setdefault("worker", "")
    normalized.setdefault("browser_session", "")
    normalized.setdefault("next_action", "")
    normalized.setdefault("profile_signature", "")
    normalized.setdefault("document_signatures", [])
    normalized.setdefault("evidence_refs", [])
    normalized.setdefault("inferred_answer_count", 0)
    normalized.setdefault("generated_answer_count", 0)
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
    ):
        if later.get(field):
            current[field] = later[field]
    for field in ("document_signatures", "evidence_refs"):
        if later.get(field):
            current[field] = later[field]


def normalize_state(state: dict) -> dict:
    """Upgrade append-only application events into one lifecycle per run and job."""
    for run in state["runs"]:
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


def normalize_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip() if value else ""


def canonicalize_url(value: str | None) -> str:
    if not value:
        return ""

    parts = urlsplit(value.strip())
    hostname = (parts.hostname or "").lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    netloc = hostname
    if parts.port:
        netloc = f"{netloc}:{parts.port}"

    filtered_query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS and not key.lower().startswith("utm_")
    ]
    path = parts.path.rstrip("/") or "/"
    if hostname == "app.joinhandshake.com" and re.fullmatch(r"/job-search/\d+", path):
        filtered_query = []
    return urlunsplit(
        (parts.scheme.lower(), netloc, path, urlencode(sorted(filtered_query)), "")
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
        "blocked": sum(item["status"] == "blocked" for item in run["applications"]),
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
        "recorded_at": application["recorded_at"],
    }


def iter_submitted_applications(state: dict) -> Iterator[dict]:
    for run in state["runs"]:
        for application in run["applications"]:
            if application["status"] == "submitted":
                yield {"run_id": run["id"], **application}


def exact_match(
    application: dict,
    *,
    canonical_url: str,
    site: str | None,
    job_id: str | None,
) -> bool:
    same_url = bool(
        canonical_url and application.get("canonical_url") == canonical_url
    )
    same_provider_job = bool(
        has_provider_identifier(site, job_id)
        and normalize_text(application.get("site")) == normalize_text(site)
        and normalize_text(application.get("job_id")) == normalize_text(job_id)
    )
    return same_url or same_provider_job


def find_prior_submission(
    state: dict,
    *,
    url: str | None,
    site: str | None,
    job_id: str | None,
) -> dict | None:
    canonical_url = canonicalize_url(url)
    for application in iter_submitted_applications(state):
        if exact_match(
            application,
            canonical_url=canonical_url,
            site=site,
            job_id=job_id,
        ):
            return application_identity(application)
    return None


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
            "possible_match": possible,
        }
    )


def nonnegative_integer(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("count must not be negative")
    return number


def validate_record_request(
    args: argparse.Namespace,
    *,
    existing: dict | None,
    url: str,
) -> None:
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
    if args.status == "blocked":
        if not args.reason_code.strip() or not args.note.strip():
            raise SystemExit("A blocked application requires --reason-code and --note.")
        if not args.browser_session.strip() or not args.next_action.strip():
            raise SystemExit(
                "A blocked application requires --browser-session and --next-action."
            )
    if args.status == "in_progress" and not (
        args.worker.strip() or (existing and existing.get("worker"))
    ):
        raise SystemExit("An in-progress application requires --worker.")

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
            "reason_code": args.reason_code.strip() if args.status == "blocked" else "",
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
        }
    )
    application["canonical_url"] = canonicalize_url(application["url"])
    application["transitions"].append(
        {
            "at": now,
            "from": previous_status,
            "to": args.status,
            "reason_code": application["reason_code"],
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
    validate_record_request(args, existing=existing, url=url)

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
    summary = run_summary(run)
    if summary["remaining"] == 0:
        run["status"] = "complete"
        run["completed_at"] = utc_now()
        state["active_run_id"] = None
        summary = run_summary(run)

    save_state(state_path, state)
    save_successful_applications(successful_applications_file, state)
    print_json({"recorded": application, "run": summary})


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
    record.add_argument("--reopen", action="store_true")

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
    elif args.command == "amend":
        amend_run(args, state, state_path)
        save_successful_applications(successful_applications_file, state)
    elif args.command == "abandon":
        abandon_run(args, state, state_path)
        save_successful_applications(successful_applications_file, state)


if __name__ == "__main__":
    main()
