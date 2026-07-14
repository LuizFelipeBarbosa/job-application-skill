# Signed-in browser workflow

Use this guide before discovering jobs or completing applications in the user's browser.

## Connect and preserve the session

1. Load and follow the available Chrome-control skill. Require the Chrome plugin, extension, and active profile connection needed for signed-in browsing and file uploads.
2. Use a distinct persistent browser binding for the run and give its task or tab group a descriptive name. Reuse that binding across continuations.
3. Reuse or claim a matching open tab before creating another one. Use the profile's existing signed-in session without inspecting passwords, cookies, local storage, credentials, or authentication tokens. Store a password only through the local OS-vault manager after the user explicitly authorizes a new account under the core skill's account-creation workflow.
4. If the profile is signed out, ask the user to sign in in Chrome and tell you when it is ready. Do not change browsers to bypass authentication.

## Recover the guarded compatibility failure

Attempt normal Chrome initialization first. If it fails with exactly `Cannot redefine property: process`, inspect the active Chrome plugin manifest. Only when its version is exactly `26.707.71524`, read and follow `references/chrome-26.707.71524-process-workaround.md` completely.

Do not apply that workaround proactively, for another error, or to another plugin version. For every other initialization failure, leave installed plugin files unchanged and follow the Chrome-control skill's current troubleshooting instructions.

## Upload files safely

- Use only paths and upload restrictions recorded in the candidate profile or explicitly supplied for the current run.
- Inspect the local file, then verify the employer, role, and application destination immediately before uploading.
- Upload resumes by default when authorized and relevant. Upload cover letters, transcripts, portfolios, or other files only when the application calls for them or the user directs it.
- Never upload candidate files to resume optimizers, public profiles, recruiter messages, unrelated services, or a mismatched application.
- If Chrome cannot access a local file, ask the user to open **Chrome > Extensions > Manage Extensions**, select the Codex extension's **Details**, enable **Allow access to file URLs**, and restart the Chrome task.

## Handle verification challenges

- Use an authorized Gmail connector to retrieve a recent email verification or MFA code only when it unambiguously matches the current verified employer or ATS flow. Use Computer Use to enter a supported code, following its confirmation policy for sensitive authentication data.
- For CAPTCHA, load and follow the Computer Use skill. Inspect the visible challenge and request its mandatory action-time confirmation immediately before attempting the ordinary on-page interaction. Never use external solvers, extensions, token replay, anti-bot evasion, or another bypass technique.
- Keep unsupported MFA, identity proof, security-key, biometric, device-approval, or personal-knowledge challenges open and identify the site or tab in the handoff. Ask the user to complete the exact action, then inspect and resume the same application.
- Never manipulate queues, rate limits, anti-bot controls, or challenge tokens.
- Preserve unrelated tabs and account state. Do not open messages, change profiles or preferences, save searches, or interact with unrelated features unless the user asks.

## Confirm submission

Treat a visible final success page or confirmation number as sufficient evidence. Use a confirmation email only when the user separately authorizes email access. Do not count a submission button click, a loading state, or an unverified redirect as success.
