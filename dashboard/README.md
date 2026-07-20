# Job Search Command Center

A private, local Next.js dashboard for the tracker maintained by the
`apply-to-jobs` skill.

## Start

```bash
pnpm install --frozen-lockfile
pnpm dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Both development and
production scripts bind to `127.0.0.1` rather than exposing the dashboard to
the local network.

The ordinary `dev` and `start` commands keep Account Vault disabled. Enable it for one process with `pnpm dev:vault` or `pnpm start:vault`, then open the printed URL. Each launch creates a fresh 256-bit token in the URL fragment. Browser code removes the fragment, stores the token only in session storage, and sends it as a bearer header. Do not set or persist `JOB_DASHBOARD_VAULT_TOKEN` yourself.

The default workspace is the dashboard directory's parent. Copy `.env.example`
to `.env.local` only when paths or the display timezone need overrides.

## Data boundaries

- `private/application-state.json` is the authoritative automation tracker.
- `private/successful-applications.json` is read only for reconciliation.
- `private/application-outcomes.json` is created on the first outcome update and
  stores only career stages, notes, and follow-ups. Writes use mode `0600` and
  same-directory atomic replacement.
- `private/accounts.json` contains non-secret site and username metadata.
- Passwords stay in the OS credential vault. The browser receives only a copy
  confirmation and a 30-second clipboard countdown. A detached digest-only
  guard clears the clipboard only while it still contains the copied password.

Account Vault accepts credential actions only from a loopback host with a
valid per-launch bearer token, same-origin fetch metadata, matching origin,
SameSite session cookie, and CSRF token. A global copy rate limit also applies. It resolves the
requested opaque account ID against `accounts.json` before invoking
`password_manager.py` with an argument array and no shell. It cannot reveal,
create, replace, or delete credentials.

## Checks

```bash
pnpm typecheck
pnpm lint
pnpm test
pnpm build
pnpm exec playwright install chromium
pnpm test:e2e
```

Playwright uses synthetic files under `tests/fixtures/` and an ignored
`.test-runtime/` outcome store; it never edits the real private tracker.

The local `/diagnostics/browser` route verifies navigation, form entry, screenshot inspection, synthetic file upload, and confirmation-state reading without job-site or candidate data.
