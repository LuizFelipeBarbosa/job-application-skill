---
name: apply-to-jobs
description: Find matching roles and submit a bounded batch of job applications using authorized candidate materials, company and role research, parallel subagents, a signed-in browser session, authorized Gmail access, and Computer Use for supported verification challenges. Coordinate distinct application workers so user-blocked forms do not stall the batch. Build or refresh a private candidate profile, infer and fill supported answers, tailor prose, create and email-verify required ATS accounts under standing authorization, handle supported MFA and CAPTCHAs subject to action-time confirmation, store generated passwords in the OS credential vault, prevent duplicates, resume interrupted batches, and count only confirmed applications. Use when the user asks to apply to jobs or continue a bounded application batch through configured job sites or ATS systems, including Handshake. Do not use for research-only job searches or resume review.
---

# Apply to Jobs

Execute a truthful, user-bounded job search. Automatically resolve ordinary application questions from authorized candidate evidence and verified company research. When subagents are available and the target exceeds one application, default to a coordinator-and-workers approach so independent applications progress concurrently. Continue until the requested number of applications is confirmed, the user pauses the run, or no safe alternative remains.

## Resolve the run

1. Resolve the target count and criteria from the user's newest explicit request. When goal tools are available and a relevant goal is active, call `get_goal` at the start of each continuation and use it as durable context, but let newer explicit instructions refine it. Never require `/goal` syntax or an explicit `$apply-to-jobs` mention.
2. Require one unambiguous positive target count. If it is missing, ask only how many applications to submit. Do not tell the user to rephrase the request as a goal.
3. Treat an explicit request to **apply** or **submit** as authorization for ordinary job-application data transmission, authorized document uploads, and final submission. If the user asks only to find, browse, recommend, or research jobs, stop before transmitting private data or submitting.
4. Read `config/job-sites.json` from the workspace when it exists. Use sources named by the user first, then enabled sources by ascending priority. Resolve relative instruction paths from the skill root. If no configuration exists, use an available source-specific reference only when it matches the user's request.
5. Resolve `<skill-root>` as the directory containing this `SKILL.md`; never assume the skill is installed under `.agents/skills`. Keep runtime state under the current workspace's ignored `private/` directory.
6. Read `references/profile.md` completely, then build or incrementally refresh the candidate profile from authorized materials and explicit answers. On first use, tell the user once that reusable answers are stored locally under `private/` and that they may label any answer `session only`.
7. Ask only questions that block a useful search or cannot be answered safely by the automatic answer-resolution workflow. Do not request an address, exact start date, compensation, references, demographic choices, or screening answers merely because a later form might ask for them.
8. Inspect the tracker before starting. Resume a compatible active run. When the user explicitly changes its target or objective, amend the active or latest completed run instead of discarding its completed work. Preserve all prior application history.
9. Before browser work, run `scripts/password_manager.py backend` when the batch may require account creation. If the pinned `keyring` dependency or a supported OS vault is unavailable, ask the user to install `requirements.txt` or configure the vault before opening application forms.

Start or resume a run with the tracker:

```bash
python3 "<skill-root>/scripts/tracker.py" \
  --state "<workspace>/private/application-state.json" \
  start --target 10 --objective "Apply to 10 entry-level data science jobs"
```

Amend or reopen a run without discarding confirmed submissions:

```bash
python3 "<skill-root>/scripts/tracker.py" \
  --state "<workspace>/private/application-state.json" \
  amend --target 15 --objective "Apply to 15 entry-level data science jobs"
```

Before browser work, give the user a compact run brief containing the target, key filters, selected sources, default application documents, and submission mode. Default an explicit bounded application request to automatic submission of ordinary forms, while honoring a saved or current instruction to review each submission or review exceptions only.

## Drive the batch with subagents

When subagent tools are available and the target exceeds one application, use them as the default execution model:

1. Keep the primary agent as coordinator. Make it solely responsible for the application queue, tracker and profile writes, target reconciliation, user communication, and assignment of unique jobs. Do not let workers mutate shared JSON or profile files concurrently.
2. Build a queue of verified, nonduplicate roles. Before assigning a worker, have the coordinator record that role as `in_progress` with a stable job ID or canonical URL, worker name, and browser session. A successful command reserves the current worker's slot; use the returned `available_slots` only to decide whether another worker may be dispatched. Give the worker the returned application ID, run criteria, submission mode, authorized document paths, profile path and signature, source instructions, and dedicated browser tab or session name.
3. Run as many independent application workers as the available concurrency and browser tooling safely support, but never exceed the tracker's reserved capacity. Reuse idle workers for later applications rather than growing the pool without bound.
4. Let each worker research its employer, evaluate fit, resolve answers, and complete its assigned application end to end when dedicated browser tabs or sessions can be controlled independently. If browser control is effectively single-user, parallelize company research, qualification checks, and answer drafting in workers while the coordinator performs browser mutations.
5. Serialize shared sensitive operations, including credential creation, clipboard use, Gmail verification or MFA retrieval, and updates to the tracker, account index, or candidate profile. Continue unrelated worker tasks while one of these operations is in progress.
6. Require each worker to return a compact handoff with the application ID, employer, role, stable identifier, URL, status, confirmation evidence, dedicated tab or session, and either the exact blocker and next action or the completed result. Include the profile signature, authorized-document signatures, counts of conservatively inferred and role-specific generated answers, and non-sensitive evidence references such as profile sections, document hashes, posting sections, or official URLs. Never include private answer text in the tracker handoff.
7. When a worker reaches a question, verification step, or unsupported challenge requiring the user, preserve the page and return the handoff instead of waiting. Have the coordinator update the same application to `blocked` with its reason, note, browser session, and next action; this releases its reserved slot. Dispatch another queued application only when `available_slots` permits it. Before resuming a blocked application, transition that application ID back to `in_progress`; wait if no slot is available.
8. Route every user-facing question through the coordinator. Batch nonurgent blockers, share a newly saved answer with all relevant workers, and interrupt the user immediately only for time-sensitive actions or when all remaining applications depend on user input.
9. Reconcile confirmed submissions after every worker result. A worker may click the final Submit control only after the coordinator confirms that its application is still reserved immediately before submission. Stop dispatching, transition unneeded reservations to `skipped` before submission, and preserve resumable handoffs as soon as the target is reached or the user pauses the run.

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

Reserve a slot before assigning browser work:

```bash
python3 "<skill-root>/scripts/tracker.py" \
  --state "<workspace>/private/application-state.json" \
  record --status in_progress --worker "application-worker-1" \
  --browser-session "Acme data scientist" --site "Handshake" --job-id "123" \
  --company "Example" --title "Data Scientist" --location "Seattle, WA" \
  --url "https://app.joinhandshake.com/job-search/123"
```

If a metadata-only `possible_match` is verified as a distinct opening, add `--allow-possible-match` when creating its reserved lifecycle. The returned application ID carries that resolution through later transitions. Never use the override without checking the prior role.

## Resolve application answers automatically

- Treat automatic completion as the default. Do not ask the user merely because an answer is not written verbatim in the profile.
- Follow the answer-resolution workflow in `references/profile.md`: use current user directions and saved answers first, then authorized candidate materials, conservative calculations or logical inferences from that evidence, the live posting and form context, and verified company or role research where relevant.
- Research the employer before answering company-, team-, product-, mission-, values-, or role-specific questions. Prefer the live posting and official company sources; supplement them with current, reliable sources only when needed. Verify that every source refers to the same employer and role.
- Use company research to explain role fit and write tailored answers such as **Why this company?**, **Why this role?**, or **What interests you about our work?** Combine verified company facts with supported candidate experience, skills, and goals. Paraphrase source material and never claim personal history, product use, referrals, or pre-existing enthusiasm that the candidate materials do not support.
- Answer factual and qualification questions when the response is directly supported or conservatively derivable. Use the closest supported dropdown choice, do not round experience upward, do not double-count overlapping work, and do not inflate proficiency or responsibility.
- Track only non-sensitive provenance for every inferred or generated answer: the supporting profile section, authorized-document signature, posting section, or official research URL. Record counts and evidence references in the coordinator handoff; do not copy private form answers into tracker state.
- Never use company research or general plausibility to create candidate facts, credentials, preferences, commitments, availability, compensation requirements, personal stories, legal status, protected traits, or sensitive answers.
- For an unsupported optional question, leave it blank or select a neutral **Prefer not to answer** or **Decline** option when available. Ask the exact question only when it is required, no supported inference or neutral response exists, and the application cannot proceed safely without the user's answer.

## Complete each application

For each application:

1. Verify the employer, title, location, posting status, core qualifications, eligibility language, and destination URL.
2. Resolve and fill every application question possible through the automatic answer-resolution workflow. Fill candidate facts only when supported by the profile, authorized materials, or a conservative derivation from them. Never invent metrics, titles, dates, technologies, referrals, or personal stories.
3. Research the company and role when a question calls for employer context, motivation, or fit, then write a concise answer grounded in verified company facts and supported candidate evidence. Do not leave ordinary narrative questions unanswered merely because no reusable response exists.
4. Answer work authorization, immigration, sponsorship, citizenship, clearance, and voluntary self-identification questions exactly as explicitly saved or supplied. Never infer protected or sensitive answers.
5. Tailor short prose using supported facts. Do not convert agent-authored, role-specific prose into durable candidate facts.
6. Upload only authorized documents to the matching application form. Inspect each file locally and verify the employer and role immediately before uploading it.
7. Review all answers before submission, especially identity, contact information, dates, education, work authorization, and document selection.
8. Follow the selected submission mode. Submit automatically only when the run authorizes it, every required answer is supported, and the form shows no unresolved error.
9. Confirm success from a final page or confirmation number. When an authorized Gmail connection is available, search narrowly for a recent confirmation message tied to the current employer, ATS, role, or application. Do not inspect unrelated messages. A click on **Submit** without confirmation does not count.
10. Return the result to the coordinator immediately. Have the coordinator record it, including the provider job ID and location when available:

```bash
python3 "<skill-root>/scripts/tracker.py" \
  --state "<workspace>/private/application-state.json" \
  record --status submitted --application-id "<application-id>" \
  --site "Handshake" --job-id "123" \
  --company "Example" --title "Data Scientist" --location "Seattle, WA" \
  --url "https://app.joinhandshake.com/job-search/123" \
  --profile-signature "sha256:<profile-hash>" \
  --document-signature "resume.pdf sha256:<document-hash>" \
  --inferred-answer-count 1 --generated-answer-count 1 \
  --evidence-ref "profile:Employment" \
  --evidence-ref "https://example.com/about" \
  --confirmation "Application submitted page displayed"
```

The tracker maintains `private/successful-applications.json` as a private, read-only projection containing confirmed submissions from every run.

## Create and verify required accounts

When an application requires a new account and no reusable signed-in account exists:

1. Verify that the registration page belongs to the configured job source, employer, or employer-authorized ATS. Never create an account on a mismatched or unverified domain.
2. Treat an explicit request to submit a bounded application batch as standing authorization to create accounts required solely for those applications. Do not ask for per-account approval. Use the candidate's authorized application email, accept only ordinary account terms and privacy notices, decline optional marketing, and avoid creating a duplicate when an existing account is detected.
3. Use `<skill-root>/scripts/password_manager.py` to generate a unique password in the validated local operating-system credential vault. Complete the dependency and backend preflight before browser work. Never fall back to an unsupported, chained, plaintext, or third-party file backend; invent a shared password; reuse another site's password; pass a password on a command line; print it; write it to the candidate profile; or store it in repository files.
4. Copy the stored password to the local clipboard with the manager, paste it into the password and confirmation fields without reading it, then clear the clipboard immediately. If secure clipboard paste is unavailable, ask the user to set the password themselves; never reveal the stored value in tool output.
5. When an authorized Gmail connection is available, complete ordinary account email verification without asking the user. Search only for recent messages tied to the current verified site, sender domain, or registration attempt. Open only the relevant message, extract the verification link or code, and verify that any link resolves to the expected employer, ATS, or identity-provider domain before using it. Do not read unrelated messages; do not send, delete, archive, label, forward, or otherwise modify email.
6. Handle supported email-code MFA the same way: use authorized Gmail access to retrieve only the matching recent code, verify the destination site, and use Computer Use to enter it. Follow the Computer Use confirmation policy for transmitting an OTP or other sensitive authentication data. If Gmail access is unavailable, the matching message is ambiguous, or the challenge requires an authenticator app, security key, biometric, push approval, SMS unavailable to the agent, or user knowledge, keep the page open and ask the user to complete it.
7. For a CAPTCHA, load and follow the Computer Use skill, inspect the visible challenge, and request the required action-time confirmation immediately before attempting it. After confirmation, complete only the ordinary on-page interaction and resume the same registration. Never use a CAPTCHA-solving service, extension, token replay, anti-bot evasion, or another bypass technique. Hand off challenges that require personal knowledge, identity proof, biometrics, or an unavailable device.
8. Stop and ask before accepting unusual terms, starting a paid service, creating a public profile, opting into marketing, or changing an existing account's password or security settings.
9. If registration fails permanently, delete the newly generated credential. If it succeeds, leave the credential in the local vault and the non-secret account index under `<workspace>/private/accounts.json`.

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

- Attempt supported email-code MFA and ordinary on-page CAPTCHA handling through the account-verification workflow above. Keep unsupported challenges open in the named Chrome tab, ask the user to complete the exact required action, and resume the same application afterward. Never outsource, bypass, weaken, or evade security controls.
- Do not take timed assessments, coding tests, recorded interviews, or personality tests unless the user explicitly includes them.
- Accept ordinary privacy notices, truthful-application certifications, and electronic-signature acknowledgements required for submission. Stop on unusual releases, arbitration choices, financial commitments, or terms unrelated to a normal application.
- Update unresolved required answers or other retriable interruptions to `blocked` with the existing `--application-id`, a concise `--reason-code`, `--note`, `--browser-session`, and `--next-action`. Preserve the worker handoff and continue dispatching other eligible roles only when the released slot makes `available_slots` positive.
- Record closed, ineligible, verified duplicate, or poor-fit roles as `skipped` when preserving that result prevents repeated work.
- Batch nonurgent questions. Interrupt immediately only when the current page requires the user's direct action or all remaining work depends on one answer.

## Keep the user oriented

- Have only the coordinator send user-facing updates. Send a short progress update after every three confirmed submissions or any material event such as a sign-in request, human-verification handoff, source exhaustion, or repeated site failure.
- State progress as confirmed submissions versus target, plus useful blocked or skipped counts. Do not expose private form answers.
- When user action is required, name the site or tab, describe the exact action, and say what will resume afterward.
- Before reporting completion, reconcile new profile answers and check tracker status one final time.

## Finish exactly at the target

- Re-check tracker status and the application's reservation immediately before each submission. Stop when `remaining` is zero; never submit an unreserved blocked application while another application holds the last available slot.
- Report the confirmed count, source sites, submitted companies and roles, and unresolved blockers without exposing private data.
- When a relevant active goal exists, update it according to the goal tool contract. If the user pauses or cancels the run, stop applying and preserve resumable state.
- Never turn a bounded request into an unbounded or scheduled application process.
