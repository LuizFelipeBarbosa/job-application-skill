---
name: apply-to-jobs
description: Find matching roles and submit a bounded batch of job applications using authorized candidate materials and a signed-in browser session. Build or refresh a private reusable candidate profile, ask only for information required by the current search or form, ask permission before creating required accounts, store generated passwords in the local OS credential vault, prevent duplicate submissions, resume interrupted batches, and count only confirmed applications. Use when the user asks to apply to jobs or continue a job-application batch through configured job sites or employer ATS systems, including Handshake. Do not use for research-only job searches or resume review.
---

# Apply to Jobs

Execute a truthful, user-bounded job search. Continue until the requested number of applications is confirmed, the user pauses the run, or no safe alternative remains.

## Resolve the run

1. Resolve the target count and criteria from the user's newest explicit request. When goal tools are available and a relevant goal is active, call `get_goal` at the start of each continuation and use it as durable context, but let newer explicit instructions refine it. Never require `/goal` syntax or an explicit `$apply-to-jobs` mention.
2. Require one unambiguous positive target count. If it is missing, ask only how many applications to submit. Do not tell the user to rephrase the request as a goal.
3. Treat an explicit request to **apply** or **submit** as authorization for ordinary job-application data transmission, authorized document uploads, and final submission. If the user asks only to find, browse, recommend, or research jobs, stop before transmitting private data or submitting.
4. Read `config/job-sites.json` from the workspace when it exists. Use sources named by the user first, then enabled sources by ascending priority. Resolve relative instruction paths from the skill root. If no configuration exists, use an available source-specific reference only when it matches the user's request.
5. Resolve `<skill-root>` as the directory containing this `SKILL.md`; never assume the skill is installed under `.agents/skills`. Keep runtime state under the current workspace's ignored `private/` directory.
6. Read `references/profile.md` completely, then build or incrementally refresh the candidate profile from authorized materials and explicit answers. On first use, tell the user once that reusable answers are stored locally under `private/` and that they may label any answer `session only`.
7. Ask only questions that block a useful search or the next likely application. Do not request an address, exact start date, compensation, references, demographic choices, or screening answers merely because a later form might ask for them.
8. Inspect the tracker before starting. Resume a compatible active run. When the user explicitly changes its target or objective, amend it instead of abandoning its completed work. Preserve all prior application history.

Start or resume a run with the tracker:

```bash
python3 "<skill-root>/scripts/tracker.py" \
  --state "<workspace>/private/application-state.json" \
  start --target 10 --objective "Apply to 10 entry-level data science jobs"
```

Amend an active run without discarding confirmed submissions:

```bash
python3 "<skill-root>/scripts/tracker.py" \
  --state "<workspace>/private/application-state.json" \
  amend --target 15 --objective "Apply to 15 entry-level data science jobs"
```

Before browser work, give the user a compact run brief containing the target, key filters, selected sources, default application documents, and submission mode. Default an explicit bounded application request to automatic submission of ordinary forms, while honoring a saved or current instruction to review each submission or review exceptions only.

## Prepare the browser and sources

1. Read `references/browser.md` completely before browser work and follow the available Chrome-control skill it identifies. Use the user's signed-in Chrome session for discovery, form completion, uploads, redirects, and confirmation checks.
2. Read only the source-specific instructions selected for the run. Read `references/handshake.md` completely when Handshake is selected.
3. Reuse a matching tab and persistent browser binding when possible. Leave unrelated account state, messages, profiles, preferences, and saved searches unchanged.

## Find eligible roles

- Follow the run's role, seniority, location, work-arrangement, freshness, compensation, company, industry, and source criteria. Derive reasonable role families from the private profile when the user supplies only a count, but do not hardcode one candidate's background into the skill.
- Verify that each posting is open and that its employer, title, location, qualifications, and eligibility requirements match the candidate's saved facts and directions.
- Follow a configured discovery source's job-specific application link to a verified employer career site or ATS when allowed. If it lands on a general careers page, locate only the same position by employer, title, location, or job identifier; do not silently substitute another role.
- Stop on employer or job mismatches, impersonation signals, payment requests, credential requests, or financial-data requests unrelated to a normal application.
- Check the tracker before opening a form. Prefer a stable provider job ID or canonical job URL; include location when only role metadata is available:

```bash
python3 "<skill-root>/scripts/tracker.py" \
  --state "<workspace>/private/application-state.json" \
  check --site "Handshake" --job-id "123" \
  --url "https://app.joinhandshake.com/job-search/123" \
  --company "Example" --title "Data Scientist" --location "Seattle, WA"
```

Treat `already_submitted: true` as a duplicate. Treat `possible_match` as a prompt to verify identifiers, not as proof that the role is a duplicate.

## Complete each application

For each application:

1. Verify the employer, title, location, posting status, core qualifications, eligibility language, and destination URL.
2. Fill only facts supported by the candidate profile or authorized source documents. Never invent metrics, titles, dates, technologies, motivations, referrals, or personal stories.
3. Perform the source-first answer check in `references/profile.md` whenever a form introduces a missing or ambiguous required answer. Ask the exact question only when the form cannot proceed safely; do not ask a broad category of hypothetical questions.
4. Answer work authorization, immigration, sponsorship, citizenship, clearance, and voluntary self-identification questions exactly as explicitly saved or supplied. Never infer protected or sensitive answers.
5. Tailor short prose using supported facts. Do not convert agent-authored, role-specific prose into durable candidate facts.
6. Upload only authorized documents to the matching application form. Inspect each file locally and verify the employer and role immediately before uploading it.
7. Review all answers before submission, especially identity, contact information, dates, education, work authorization, and document selection.
8. Follow the selected submission mode. Submit automatically only when the run authorizes it, every required answer is supported, and the form shows no unresolved error.
9. Confirm success from a final page or confirmation number. Use a confirmation email only when the user has separately authorized access to their email. A click on **Submit** without confirmation does not count.
10. Record the result immediately, including the provider job ID and location when available:

```bash
python3 "<skill-root>/scripts/tracker.py" \
  --state "<workspace>/private/application-state.json" \
  record --status submitted --site "Handshake" --job-id "123" \
  --company "Example" --title "Data Scientist" --location "Seattle, WA" \
  --url "https://app.joinhandshake.com/job-search/123" \
  --confirmation "Application submitted page displayed"
```

The tracker maintains `private/successful-applications.json` as a private, read-only projection containing confirmed submissions from every run.

## Create accounts only with permission

When an application requires a new account and no reusable signed-in account exists:

1. Verify that the registration page belongs to the configured job source, employer, or employer-authorized ATS. Never create an account on a mismatched or unverified domain.
2. Ask for explicit permission before entering registration data or selecting **Create account**. Name the site, the username or email that will be used, why the account is required, and that creating it may accept the site's ordinary account terms and privacy notice. Permission applies only to that named site and account; ordinary authorization to submit applications is not account-creation permission. Do not proceed until the user gives an unambiguous affirmative response. Use this concise form:

   > This application requires an account at `<site>` using `<username>`. Creating it may accept the site's ordinary account terms and privacy notice. May I create this account and store a unique password in your local OS credential vault?
3. If permission is declined, do not create the account or a duplicate account. Record the application as `blocked` and continue with other eligible roles. If the user already has an account, ask them to sign in rather than creating another one.
4. After permission is granted, use `<skill-root>/scripts/password_manager.py` to generate a unique password in the local operating-system credential vault. If its `keyring` dependency is unavailable, ask the user to install `<skill-root>/requirements.txt` and wait. Never fall back to a plaintext credential backend, invent a shared password, reuse another site's password, pass a password on a command line, print it, write it to the candidate profile, or store it in repository files.
5. Copy the stored password to the local clipboard with the manager, paste it into the password and confirmation fields without reading it, then clear the clipboard immediately. If secure clipboard paste is unavailable, ask the user to set the password themselves; never reveal the stored value in tool output.
6. Pause for the user to complete email verification, MFA, CAPTCHA, or another human-verification step. Resume the same registration and application afterward.
7. Stop and ask again before accepting unusual terms, starting a paid service, creating a public profile, opting into marketing, or changing an existing account's password or security settings.
8. If registration fails permanently, delete the newly generated credential. If it succeeds, leave the credential in the local vault and the non-secret account index under `<workspace>/private/accounts.json`.

Generate and store a password without printing it:

```bash
python3 "<skill-root>/scripts/password_manager.py" \
  --metadata "<workspace>/private/accounts.json" \
  generate --site "careers.example.com" --username "candidate@example.com"
```

Copy it for immediate paste, then clear the clipboard after both password fields are filled:

```bash
python3 "<skill-root>/scripts/password_manager.py" \
  --metadata "<workspace>/private/accounts.json" \
  copy --site "careers.example.com" --username "candidate@example.com"

python3 "<skill-root>/scripts/password_manager.py" clear-clipboard
```

## Handle blockers without losing momentum

- Keep a CAPTCHA, MFA prompt, or other human-verification page open and ask the user to complete it directly in the named Chrome tab. Resume the same application afterward. Never automate, outsource, or bypass security controls.
- Do not take timed assessments, coding tests, recorded interviews, or personality tests unless the user explicitly includes them.
- Accept ordinary privacy notices, truthful-application certifications, and electronic-signature acknowledgements required for submission. Stop on unusual releases, arbitration choices, financial commitments, or terms unrelated to a normal application.
- Record unresolved required answers or other retriable interruptions as `blocked` with a concise `--reason-code` and note, then continue while other eligible roles remain.
- Record closed, ineligible, verified duplicate, or poor-fit roles as `skipped` when preserving that result prevents repeated work.
- Batch nonurgent questions. Interrupt immediately only when the current page requires the user's direct action or all remaining work depends on one answer.

## Keep the user oriented

- Send a short progress update after every three confirmed submissions or any material event such as a sign-in request, human-verification handoff, source exhaustion, or repeated site failure.
- State progress as confirmed submissions versus target, plus useful blocked or skipped counts. Do not expose private form answers.
- When user action is required, name the site or tab, describe the exact action, and say what will resume afterward.
- Before reporting completion, reconcile new profile answers and check tracker status one final time.

## Finish exactly at the target

- Re-check tracker status before each new submission and stop when `remaining` is zero.
- Report the confirmed count, source sites, submitted companies and roles, and unresolved blockers without exposing private data.
- When a relevant active goal exists, update it according to the goal tool contract. If the user pauses or cancels the run, stop applying and preserve resumable state.
- Never turn a bounded request into an unbounded or scheduled application process.
