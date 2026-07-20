# External capability preflight

Run these probes only when the user explicitly asks to test external integrations. Do not combine them with a normal local `doctor` run.

1. Run `scripts/doctor.py --format json` and stop on required failures.
2. Gmail: call only the connected-profile operation. Report connected or unavailable without reading messages.
3. Chrome: initialize the official Chrome controls in the active profile and open only the local dashboard diagnostic route. Do not inspect history, cookies, storage, passwords, or unrelated tabs.
4. File upload: use only the bundled synthetic text fixture on the diagnostic route.
5. Computer Use: inspect and toggle only the diagnostic route's harmless control. Confirm that Screen Recording and Accessibility are available on macOS or that the active desktop is visible on Windows.
6. Close the diagnostic tab and report pass, warning, or exact remediation. Do not open a job site, mailbox message, credential, or verification challenge.

Linux receives a warning because full Computer Use is unavailable; local tracking, Gmail, Chrome where supported, the dashboard, and supported OS vaults may still be used.
