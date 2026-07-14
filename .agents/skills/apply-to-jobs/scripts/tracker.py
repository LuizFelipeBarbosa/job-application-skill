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
RECORD_STATUSES = ("submitted", "blocked", "skipped")


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
    return state


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
    return urlunsplit((parts.scheme.lower(), netloc, path, urlencode(sorted(filtered_query)), ""))


def get_active_run(state: dict, *, require_active: bool = False) -> dict | None:
    run_id = state.get("active_run_id")
    run = next((item for item in state["runs"] if item.get("id") == run_id), None)
    if run is not None and run.get("status") != "active":
        run = None
    if require_active and run is None:
        raise SystemExit("No active application run. Start one before recording results.")
    return run


def run_summary(run: dict) -> dict:
    submitted = sum(item["status"] == "submitted" for item in run["applications"])
    return {
        "run_id": run["id"],
        "status": run["status"],
        "objective": run["objective"],
        "target": run["target"],
        "submitted": submitted,
        "remaining": max(run["target"] - submitted, 0),
        "blocked": sum(item["status"] == "blocked" for item in run["applications"]),
        "skipped": sum(item["status"] == "skipped" for item in run["applications"]),
    }


def application_identity(application: dict) -> dict:
    return {
        "run_id": application["run_id"],
        "company": application["company"],
        "title": application["title"],
        "location": application.get("location", ""),
        "url": application["url"],
        "site": application.get("site", ""),
        "job_id": application.get("job_id", ""),
        "recorded_at": application["recorded_at"],
    }


def iter_submitted_applications(state: dict) -> Iterator[dict]:
    for run in state["runs"]:
        for application in run["applications"]:
            if application["status"] == "submitted":
                yield {"run_id": run["id"], **application}


def find_prior_submission(
    state: dict,
    *,
    url: str | None,
    site: str | None,
    job_id: str | None,
) -> dict | None:
    canonical_url = canonicalize_url(url)
    normalized_site = normalize_text(site)
    normalized_job_id = normalize_text(job_id)

    for application in iter_submitted_applications(state):
        same_url = canonical_url and application.get("canonical_url") == canonical_url
        same_provider_job = (
            normalized_site
            and normalized_job_id
            and normalize_text(application.get("site")) == normalized_site
            and normalize_text(application.get("job_id")) == normalized_job_id
        )
        if same_url or same_provider_job:
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
        same_location = (
            not normalized_location
            or normalize_text(application.get("location")) == normalized_location
        )
        if same_role and same_location:
            return application_identity(application)
    return None


def print_json(value: dict) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def start_run(args: argparse.Namespace, state: dict, state_path: Path) -> None:
    active_run = get_active_run(state)
    if active_run and active_run["status"] == "active":
        same_run = (
            active_run["target"] == args.target
            and normalize_text(active_run["objective"]) == normalize_text(args.objective)
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
        "id": f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid4().hex[:8]}",
        "objective": args.objective.strip(),
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
    has_exact_identifier = args.url or (args.site and args.job_id)
    has_role_metadata = args.company and args.title
    if not has_exact_identifier and not has_role_metadata:
        raise SystemExit(
            "Provide --url, both --site and --job-id, or both --company and --title."
        )
    prior = find_prior_submission(
        state, url=args.url, site=args.site, job_id=args.job_id
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


def record_application(
    args: argparse.Namespace,
    state: dict,
    state_path: Path,
    successful_applications_file: Path,
) -> None:
    run = get_active_run(state, require_active=True)
    assert run is not None

    if args.status == "submitted" and not args.confirmation.strip():
        raise SystemExit("A submitted application requires --confirmation evidence.")
    if args.status == "submitted":
        prior = find_prior_submission(
            state,
            url=args.url,
            site=args.site,
            job_id=args.job_id,
        )
        if prior is not None:
            raise SystemExit(
                "This role was already submitted: "
                f"{prior['company']} - {prior['title']} ({prior['recorded_at']})."
            )
        if run_summary(run)["remaining"] == 0:
            raise SystemExit("The active run has already reached its target.")

    application = {
        "id": uuid4().hex,
        "recorded_at": utc_now(),
        "status": args.status,
        "site": args.site.strip(),
        "company": args.company.strip(),
        "title": args.title.strip(),
        "location": args.location.strip(),
        "url": args.url.strip(),
        "canonical_url": canonicalize_url(args.url),
        "job_id": args.job_id.strip(),
        "confirmation": args.confirmation.strip(),
        "reason_code": args.reason_code.strip(),
        "note": args.note.strip(),
    }
    run["applications"].append(application)

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


def amend_run(args: argparse.Namespace, state: dict, state_path: Path) -> None:
    run = get_active_run(state, require_active=True)
    assert run is not None
    if args.target is None and args.objective is None:
        raise SystemExit("Provide --target, --objective, or both.")

    submitted = run_summary(run)["submitted"]
    target = args.target if args.target is not None else run["target"]
    if target < submitted:
        raise SystemExit(
            f"Target cannot be lower than the {submitted} confirmed submissions."
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
        if target == submitted:
            run["status"] = "complete"
            run["completed_at"] = amended_at
            state["active_run_id"] = None
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

    record = commands.add_parser("record", help="Record one application outcome.")
    record.add_argument("--status", required=True, choices=RECORD_STATUSES)
    record.add_argument("--site", default="")
    record.add_argument("--company", required=True)
    record.add_argument("--title", required=True)
    record.add_argument("--location", default="")
    record.add_argument("--url", required=True)
    record.add_argument("--job-id", default="")
    record.add_argument("--confirmation", default="")
    record.add_argument("--reason-code", default="")
    record.add_argument("--note", default="")

    amend = commands.add_parser("amend", help="Amend the active run in place.")
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
