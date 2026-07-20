"""Normalize job-provider identities without depending on tracker state."""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


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


def normalize_text(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip() if value else ""


def _normalized_url_parts(value: str | None):
    if not value:
        return None
    parts = urlsplit(value.strip())
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return None
    hostname = parts.hostname.lower()
    if hostname.startswith("www."):
        hostname = hostname[4:]
    netloc = hostname if not parts.port else f"{hostname}:{parts.port}"
    path = parts.path.rstrip("/") or "/"
    query = [
        (key, item)
        for key, item in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
        and not key.lower().startswith("utm_")
    ]
    return parts.scheme.lower(), hostname, netloc, path, query


def provider_key(site: str | None, url: str | None) -> str:
    parts = _normalized_url_parts(url)
    hostname = parts[1] if parts else ""
    if hostname == "app.joinhandshake.com":
        return "handshake"
    if "greenhouse.io" in hostname:
        return "greenhouse"
    if hostname == "jobs.lever.co":
        return "lever"
    if hostname == "jobs.ashbyhq.com":
        return "ashby"
    if "myworkdayjobs.com" in hostname:
        return "workday"
    return normalize_text(site).replace(" ", "_") or hostname


def extract_job_id(site: str | None, url: str | None, job_id: str | None) -> str:
    explicit = (job_id or "").strip()
    if explicit:
        return explicit
    parts = _normalized_url_parts(url)
    if not parts:
        return ""
    _, hostname, _, path, query = parts

    if hostname == "app.joinhandshake.com":
        match = re.fullmatch(r"/(?:job-search|jobs)/(\d+)", path)
        return match.group(1) if match else ""

    if "greenhouse.io" in hostname:
        match = re.search(r"/(?:jobs|job_app)/(\d+)(?:/|$)", path)
        if match:
            return match.group(1)
        query_values = dict(query)
        return query_values.get("gh_jid", "") or query_values.get("token", "")

    if hostname in {"jobs.lever.co", "jobs.ashbyhq.com"}:
        path_parts = [part for part in path.split("/") if part]
        if len(path_parts) >= 2:
            return path_parts[1]

    if "myworkdayjobs.com" in hostname:
        path_parts = [part for part in path.split("/") if part]
        if path_parts:
            candidate = path_parts[-1]
            if candidate.lower() not in {"job", "apply"}:
                return candidate.rsplit("_", 1)[-1]
    return ""


def canonicalize_url(value: str | None) -> str:
    parts = _normalized_url_parts(value)
    if not parts:
        return ""
    scheme, hostname, netloc, path, query = parts

    if hostname == "app.joinhandshake.com":
        match = re.fullmatch(r"/(?:job-search|jobs)/(\d+)", path)
        if match:
            path = f"/job-search/{match.group(1)}"
            query = []

    if hostname == "jobs.ashbyhq.com" and path.endswith("/application"):
        path = path[: -len("/application")]
    if hostname == "jobs.lever.co" and path.endswith("/apply"):
        path = path[: -len("/apply")]

    return urlunsplit((scheme, netloc, path or "/", urlencode(sorted(query)), ""))


def build_identity(
    *,
    site: str | None,
    url: str | None,
    job_id: str | None,
) -> dict[str, str]:
    raw_url = (url or "").strip()
    return {
        "site_key": provider_key(site, raw_url),
        "job_id": extract_job_id(site, raw_url, job_id),
        "url": raw_url,
        "canonical_url": canonicalize_url(raw_url),
    }


def identity_key(identity: dict) -> tuple[str, str, str]:
    site_key = normalize_text(identity.get("site_key")).replace(" ", "_")
    job_id = normalize_text(identity.get("job_id"))
    canonical_url = identity.get("canonical_url") or canonicalize_url(identity.get("url"))
    return site_key, job_id, canonical_url


def identities_match(left: dict, right: dict) -> bool:
    left_site, left_job, left_url = identity_key(left)
    right_site, right_job, right_url = identity_key(right)
    same_provider_job = bool(
        left_site and left_job and left_site == right_site and left_job == right_job
    )
    return same_provider_job or bool(left_url and left_url == right_url)


def add_identity(identities: list[dict], identity: dict) -> list[dict]:
    if not identity.get("canonical_url") and not (
        identity.get("site_key") and identity.get("job_id")
    ):
        return identities
    if not any(identities_match(item, identity) for item in identities):
        identities.append(identity)
    return identities


def normalize_identities(application: dict) -> list[dict]:
    identities: list[dict] = []
    for raw_identity in application.get("identities", []):
        if not isinstance(raw_identity, dict):
            continue
        add_identity(
            identities,
            build_identity(
                site=raw_identity.get("site_key") or application.get("site"),
                url=raw_identity.get("url") or raw_identity.get("canonical_url"),
                job_id=raw_identity.get("job_id"),
            ),
        )
    add_identity(
        identities,
        build_identity(
            site=application.get("site"),
            url=application.get("url"),
            job_id=application.get("job_id"),
        ),
    )
    return identities
