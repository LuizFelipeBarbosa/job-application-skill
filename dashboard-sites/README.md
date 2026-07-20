# Hosted dashboard

This owner-only, read-only companion stores a deliberately small application-data allowlist in a user-owned Cloudflare D1 database. It never exposes the local Account Vault, passwords, candidate contact details, account identifiers, browser sessions, signatures, evidence payloads, mail, verification codes, or private notes.

## Local validation

Use Node 22.13 or newer and the committed npm lockfile:

```bash
npm ci
npm run lint
npm test
npm audit --omit=dev
```

Exporting is a two-step privacy boundary. The first command transforms tracker data into the explicit allowlist. The second strictly validates that allowlist and prepares SQL for D1. Both output files are private (`0600`).

```bash
node scripts/export-sanitized-applications.mjs \
  ../private/application-state.json \
  ../private/hosted-applications.json \
  ../private/application-outcomes.json
npm run db:import:prepare -- \
  ../private/hosted-applications.json \
  ../private/hosted-applications.sql
```

Unknown exported fields, email addresses, and credential-like values are rejected. The production application API implements `GET` only and requires the Sites authentication boundary.

Local development accepts only a loopback host and uses a synthetic owner identity when Sites authentication headers are unavailable. This fallback is compiled for development only.

## Self-deployment

Never reuse an existing project ID from another installation. Create your own Cloudflare D1 database and record its generated ID only in ignored local configuration:

```bash
npx wrangler d1 create job-application-suite
cp .openai/hosting.example.json .openai/hosting.json
```

Set your user-owned Sites project ID in `.openai/hosting.json`. Keep the D1 binding named `DB`. Configure the created D1 database for that binding in your own Cloudflare/Sites project, then apply the committed migrations and sanitized import using the database name returned above:

```bash
npx wrangler d1 migrations apply job-application-suite --remote
npx wrangler d1 execute job-application-suite \
  --remote --file ../private/hosted-applications.sql
```

Run `npm test` again before publishing. Deploy only to the project ID you created. Real hosting configuration, Wrangler state, generated output, imports, and database identifiers are ignored by Git.

The hosted app assumes the deployment remains owner-only. Do not make it public: application company, title, timing, and outcome fields are intentionally non-secret but still personal career data.
