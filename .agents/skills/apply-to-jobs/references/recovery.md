# Verification-blocked application recovery

Read this guide before recovering any blocked application. Recovery never expands a completed batch implicitly.

## Start a bounded recovery run

Require a positive recovery target, then start a separate run:

```bash
python3 "<skill-root>/scripts/tracker.py" \
  --state "<workspace>/private/application-state.json" \
  start --kind recovery --target 3 \
  --objective "Recover 3 eligible verification-blocked applications"
```

Recheck the exact role before reserving it. Confirm that the employer and posting are still valid, the role remains open and eligible, and no successful submission exists. Reserve the blocked lifecycle with `recover --source-application-id`, a worker, a dedicated browser session, and fresh preflight evidence. Do not copy an old code, challenge token, password, or browser secret into the tracker.

## Serialize verification work

Let only the coordinator perform mailbox reads, credential-vault access, clipboard operations, and verification events. Record secret-free progress through `verification-event`; include only the verification type, event, browser session, and an email receipt timestamp when applicable. Never pass or store a password, OTP, verification code, message body, token, cookie, or challenge response.

## Recover email codes

1. Reopen or rebuild the exact employer form and request a new code from that live session. Record `requested` immediately.
2. Search only an authorized mailbox for the newest unambiguous employer or ATS message addressed to the application email and received after the recorded request. Do not inspect unrelated mail.
3. Record `ready` with the message receipt timestamp, then enter the code immediately in the same unchanged browser session under the applicable Computer Use confirmation policy.
4. Record `attempted`, then `succeeded` or `failed`. Never reuse a code from another request or session.
5. After one failure, reset the verification step once, request a new code, and repeat. The tracker rejects a third attempt and blocks a second failure as `session_bound_code_rejected`.

Treat codes received before the current live request as stale. If no fresh code can be requested, leave the application blocked.

## Recover other verification types

- **CAPTCHA:** Inspect the visible challenge, obtain fresh action-time confirmation, and use supported Computer Use only. Never outsource, replay, bypass, or evade it.
- **Password:** Use the validated OS credential vault and secure clipboard path. If secure transfer is unavailable, ask the user to type only the password fields, then resume.
- **Account recovery:** Use only the verified employer or ATS recovery flow and an authorized matching email. Stop before changing unrelated account security settings.
- **MFA or passkey:** Complete supported email-code MFA as above. Hand off authenticator, SMS, push approval, security-key, passkey, biometric, university identity, or device-approval steps to the user in the preserved tab.

After verification succeeds, re-audit every answer and attachment, run the duplicate check again with the final ATS identity, confirm the reservation remains available, and make at most one final submission attempt. Count only visible employer confirmation.
