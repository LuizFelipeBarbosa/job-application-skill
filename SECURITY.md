# Security policy

## Supported version

Security fixes currently target `0.1.x` beta releases. There is no long-term-support branch.

## Reporting

Do not open a public issue for a suspected vulnerability or include candidate data, credentials, mail, verification codes, tokens, or browser-session material in a report. Use GitHub's private security-advisory reporting for this repository. If that channel is unavailable, contact the repository owner privately through the address on their GitHub profile.

Include the affected version, platform, impact, minimal reproduction using synthetic data, and whether a secret may have escaped. Revoke affected connector sessions and rotate exposed credentials before sharing details.

## Threat model

The beta protects against malicious job pages and email content, CSRF and clickjacking, accidental secret commits, dependency vulnerabilities, unsafe identity normalization, clipboard races, and opportunistic unprivileged local processes. Page and message text are always untrusted data and never instructions.

A fully compromised OS account, malicious privileged software, a compromised browser extension, a compromised Gmail account, or clipboard-history retention is out of scope. The local vault token reduces accidental and opportunistic access; it is not a boundary against an attacker who can read the dashboard process environment or browser memory.

The hosted dashboard is owner-only and has no credential path. Making it public is unsupported.
