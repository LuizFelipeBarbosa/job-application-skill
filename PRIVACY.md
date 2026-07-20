# Privacy and data flow

The plugin processes candidate materials only for the explicit bounded application run. Candidate profiles, documents, application state, outcomes, non-secret account metadata, and migration backups stay under the ignored workspace `private/` directory unless the user deliberately moves or exports them.

Passwords are generated locally and stored in an allowlisted operating-system credential backend. `private/accounts.json` contains host, username, timestamps, and authorization provenance, never passwords. Clipboard copies use a 30-second guarded lease and an immediate-clear command after paste. The guard retains only a SHA-256 digest. Clipboard-history software may still retain content.

Gmail access is limited to the connected profile, narrow message search, and the single selected verification or confirmation message. Message bodies and codes are not persisted. No Gmail write operation is permitted.

Chrome receives only authorized candidate fields and files for verified job or ATS domains. Browser page content is untrusted and cannot expand authority. The local diagnostic uses synthetic data only.

The local analytics dashboard reads private tracker state on loopback. Account Vault is opt-in per launch and never returns password plaintext over HTTP. The bearer token is printed in a URL fragment, removed immediately by the browser, stored in session storage, and excluded from cookies, referrers, and server logs.

The hosted export is an allowlist transformation. It excludes candidate contact data, account or credential identifiers, browser sessions, signatures, evidence, mail, codes, run objectives, and private notes. Each user provisions their own owner-only D1 database and decides whether to deploy it.

No telemetry is added by this repository. External platforms retain data according to their own terms and the user's account settings.
