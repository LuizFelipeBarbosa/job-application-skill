# Beta limitations

- Gmail is the only email adapter. Outlook is deferred.
- Handshake is the bundled source-specific adapter. Exact posting URLs and user-named sites use the generic verified-site workflow; external employer or ATS domains may require Chrome approval.
- Browser and Computer Use confirmation requirements cannot be disabled by the skill, so a run may pause immediately before sensitive data transmission, an authentication link, or final submission.
- Account Vault is local and opt-in per launch. It does not create, rotate, display, or recover existing-account passwords.
- Schema-v1 account metadata is read during the beta but must be explicitly migrated before mutation.
- Windows ACLs are used instead of POSIX mode bits; acceptance must verify the private directory is not broadly accessible.
- Linux lacks full Computer Use parity.
- CAPTCHA support is limited to ordinary visible interactions after action-time confirmation. Outsourcing, replay, solving services, and bypass techniques are prohibited.
- Browser extensions, job sites, connector APIs, and operating systems can change independently and may require a beta patch.
- A launch token does not protect against a fully compromised local user account or privileged process.
- The hosted dashboard must remain owner-only and may contain personal career history even after sanitization.
