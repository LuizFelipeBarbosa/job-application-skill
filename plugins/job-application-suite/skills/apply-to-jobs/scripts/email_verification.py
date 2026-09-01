#!/usr/bin/env python3
"""Provider-neutral selection rules for application verification messages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
import html
import re
from typing import Literal
from urllib.parse import urlparse


MAX_VERIFICATION_AGE = timedelta(minutes=10)
MAX_ATTEMPTS = 2
ALLOWED_GMAIL_OPERATIONS = frozenset({"profile", "search", "read_selected_message"})
CODE_PATTERN = re.compile(r"(?<![A-Z0-9])([A-Z0-9]{4,8})(?![A-Z0-9])", re.IGNORECASE)
LABELED_CODE_PATTERN = re.compile(
    r"\b(?:verification\s+)?(?:code|otp|passcode)\b[^A-Z0-9]{0,20}"
    r"([A-Z0-9]{4,8})(?![A-Z0-9])",
    re.IGNORECASE,
)
LINK_PATTERN = re.compile(r'https://[^\s<>"\']+', re.IGNORECASE)


class VerificationSelectionError(ValueError):
    """The available messages cannot safely satisfy the current verification request."""


@dataclass(frozen=True)
class VerificationContext:
    requested_at: datetime
    application_address: str
    expected_identities: tuple[str, ...]
    browser_session: str
    attempted_message_ids: frozenset[str] = frozenset()
    expected_method: Literal["code", "link"] = "code"
    allowed_link_hosts: tuple[str, ...] = ()


@dataclass(frozen=True)
class VerificationMessage:
    message_id: str
    received_at: datetime
    sender: str
    recipients: tuple[str, ...]
    subject: str
    body: str


@dataclass(frozen=True)
class SelectedVerification:
    message_id: str
    received_at: datetime
    method: Literal["code", "link"]
    code: str = ""
    link: str = ""


def normalized_address(value: str) -> str:
    _, address = parseaddr(value)
    address = address.strip().casefold()
    if "@" not in address:
        raise VerificationSelectionError("Invalid email address in verification context.")
    local_part, domain = address.rsplit("@", 1)
    if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+", local_part):
        raise VerificationSelectionError("Invalid email address in verification context.")
    try:
        ascii_domain = domain.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise VerificationSelectionError("Invalid email address in verification context.") from error
    if not all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in ascii_domain.split(".")
    ):
        raise VerificationSelectionError("Invalid email address in verification context.")
    return f"{local_part}@{ascii_domain}"


def normalized_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise VerificationSelectionError("Verification timestamps must include a timezone.")
    return value.astimezone(timezone.utc)


def assert_gmail_operation(operation: str) -> None:
    if operation not in ALLOWED_GMAIL_OPERATIONS:
        raise VerificationSelectionError(f"Gmail operation is prohibited: {operation}")


def build_gmail_query(context: VerificationContext) -> str:
    requested_at = normalized_time(context.requested_at)
    address = normalized_address(context.application_address)
    identities = tuple(identity.strip() for identity in context.expected_identities if identity.strip())
    if not identities or not context.browser_session.strip():
        raise VerificationSelectionError("Expected identity and browser session are required.")
    identity_query = " OR ".join(
        '"{}"'.format(identity.replace('"', "")) for identity in identities
    )
    return f"after:{int(requested_at.timestamp())} to:{address} ({identity_query})"


def identity_matches(message: VerificationMessage, identities: tuple[str, ...]) -> bool:
    sender = parseaddr(message.sender)[1].casefold()
    haystack = f"{sender} {message.subject}".casefold()
    return any(identity.strip().casefold() in haystack for identity in identities if identity.strip())


def extract_code(body: str) -> str:
    labeled_candidates = {
        match.group(1).upper() for match in LABELED_CODE_PATTERN.finditer(body)
    }
    if len(labeled_candidates) == 1:
        return labeled_candidates.pop()
    candidates = {
        match.group(1).upper()
        for match in CODE_PATTERN.finditer(body)
        if any(character.isdigit() for character in match.group(1))
    }
    if len(candidates) != 1:
        raise VerificationSelectionError("Verification message does not contain one unambiguous code.")
    return candidates.pop()


def normalized_host(value: str) -> str:
    host = value.strip().rstrip(".").casefold()
    if not host or "/" in host or "@" in host:
        raise VerificationSelectionError("Invalid verification-link host.")
    try:
        ascii_host = host.encode("idna").decode("ascii")
    except UnicodeError as error:
        raise VerificationSelectionError("Invalid verification-link host.") from error
    if not all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in ascii_host.split(".")
    ):
        raise VerificationSelectionError("Invalid verification-link host.")
    return ascii_host


def extract_verification_link(body: str, allowed_hosts: tuple[str, ...]) -> str:
    normalized_allowed_hosts = {
        normalized_host(host) for host in allowed_hosts if host.strip()
    }
    if not normalized_allowed_hosts:
        raise VerificationSelectionError(
            "Verification-link selection requires a verified allowed host."
        )

    candidates = set()
    for raw_url in LINK_PATTERN.findall(html.unescape(body)):
        candidate = raw_url.rstrip(".,;:!?)]}")
        parsed = urlparse(candidate)
        if parsed.scheme.casefold() != "https" or not parsed.hostname:
            continue
        if parsed.username or parsed.password:
            continue
        try:
            if parsed.port not in {None, 443}:
                continue
            host = normalized_host(parsed.hostname)
        except (ValueError, VerificationSelectionError):
            continue
        if any(
            host == allowed_host or host.endswith(f".{allowed_host}")
            for allowed_host in normalized_allowed_hosts
        ):
            candidates.add(candidate)

    if len(candidates) != 1:
        raise VerificationSelectionError(
            "Verification message does not contain one unambiguous allowed HTTPS link."
        )
    return candidates.pop()


def select_verification_message(
    messages: list[VerificationMessage], context: VerificationContext
) -> SelectedVerification:
    requested_at = normalized_time(context.requested_at)
    if len(context.attempted_message_ids) >= MAX_ATTEMPTS:
        raise VerificationSelectionError("Verification attempt limit reached.")
    expected_address = normalized_address(context.application_address)
    if not context.expected_identities or not context.browser_session.strip():
        raise VerificationSelectionError("Expected identity and browser session are required.")
    if context.expected_method not in {"code", "link"}:
        raise VerificationSelectionError("Expected verification method is invalid.")

    matches = []
    for message in messages:
        received_at = normalized_time(message.received_at)
        recipient_addresses = {normalized_address(recipient) for recipient in message.recipients}
        if message.message_id in context.attempted_message_ids:
            continue
        if (
            received_at < requested_at
            or received_at - requested_at > MAX_VERIFICATION_AGE
        ):
            continue
        if expected_address not in recipient_addresses:
            continue
        if not identity_matches(message, context.expected_identities):
            continue
        matches.append(message)

    if len(matches) != 1:
        qualifier = "No" if not matches else "Multiple"
        raise VerificationSelectionError(f"{qualifier} unambiguous verification message found.")

    selected = matches[0]
    common = {
        "message_id": selected.message_id,
        "received_at": normalized_time(selected.received_at),
        "method": context.expected_method,
    }
    if context.expected_method == "link":
        return SelectedVerification(
            **common,
            link=extract_verification_link(
                selected.body,
                context.allowed_link_hosts,
            ),
        )
    return SelectedVerification(**common, code=extract_code(selected.body))
