# Job Search Command Center

A private, local Next.js dashboard for the tracker maintained by the
`apply-to-jobs` skill.

## Start

```bash
pnpm install
pnpm dev
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000). Both development and
production scripts bind to `127.0.0.1` rather than exposing the dashboard to
the local network.

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
  confirmation and a 30-second clipboard countdown.

Account Vault accepts credential actions only from a loopback host with a
matching origin, SameSite session cookie, and CSRF token. It resolves the
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
