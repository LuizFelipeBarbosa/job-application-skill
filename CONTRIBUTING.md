# Contributing

Use synthetic fixtures only. Never commit resumes, candidate profiles, contact data, tracker state, emails, browser sessions, D1 identifiers, hosting project IDs, credentials, codes, tokens, or generated private exports.

Create a focused branch, keep the primary logic path easy to follow, and include tests for behavior and privacy boundaries. Before opening a pull request, run:

```bash
python3 -m unittest discover -s plugins/job-application-suite/skills/apply-to-jobs/tests
python3 scripts/validate_release.py
cd dashboard && pnpm install --frozen-lockfile && pnpm typecheck && pnpm lint && pnpm test && pnpm build && pnpm audit --prod
cd ../dashboard-sites && npm ci && npm run lint && npm test && npm audit --omit=dev
```

Changes to authorization, Gmail permissions, password handling, hosted export fields, or browser-domain policy must explain the security impact. New email providers must implement the provider-neutral selection contract without broad mailbox permissions.
