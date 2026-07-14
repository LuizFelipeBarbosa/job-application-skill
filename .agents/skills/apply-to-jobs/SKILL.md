---
name: apply-to-jobs
description: Build or refresh a private candidate profile from user-uploaded resumes, cover letters, transcripts, portfolios, and related materials; prompt only for missing candidate directions; find jobs through configured discovery sites such as Handshake; and apply to a user-defined number through Handshake or verified external employer career and ATS sites. Use the Chrome extension for signed-in browsing and file uploads, prevent duplicates, and count only confirmed submissions. Use when the user asks Codex to search for and submit job applications, run or resume a job-application batch, target Handshake, or invokes $apply-to-jobs in a /goal objective. Do not use for resume review or job-listing research that does not include submission.
---

# Apply to Jobs

Execute a truthful, goal-bounded job search for the candidate. Continue until the requested number of confirmed applications has been submitted, the user pauses the goal, or a genuine blocker remains after exhausting safe alternatives.

## Establish the run

1. Use the active `/goal` objective as the source of the target count and search criteria. When goal tools are available, call `get_goal` at the start of every continuation.
2. Build or refresh `private/candidate-profile.md` from the user's supplied materials before asking candidate questions, starting the tracker, launching Chrome, uploading files, or searching for jobs. Follow the material workflow below.
3. Read `config/job-sites.json` and any source-specific instructions needed for the active goal.
4. Require one unambiguous positive integer for the number of applications. If it is absent, do not submit anything; ask the user to set a goal such as:

   `/goal Apply to 10 entry-level data science jobs using $apply-to-jobs.`

5. Complete the candidate-direction preflight below. Do not start the tracker, launch Chrome, upload files, or search for jobs until the user answers or explicitly declines the outstanding questions.
6. Start or resume the private tracker from the repository root:

   ```bash
   python3 .agents/skills/apply-to-jobs/scripts/tracker.py start \
     --target 10 \
     --objective "Apply to 10 entry-level data science jobs"
   ```

   If an unfinished run has a different target or objective, preserve it and ask before abandoning it. Never overwrite application history.

## Build the candidate profile from supplied materials

Before asking the user for candidate information on every new run, inspect the materials they uploaded or explicitly designated for applications. On a continuation with no new or modified materials, reuse the recorded profile and provenance instead of reprocessing unchanged files.

1. Inventory sources in this order: files attached to the current task, candidate materials the user placed in `private/`, then files already listed under `Source documents` in `private/candidate-profile.md`. Include resumes or CVs, cover letters, transcripts, portfolios, certificates, professional-profile exports, and prior application-answer documents. Do not scan unrelated workspace files.
2. If `private/candidate-profile.md` does not exist, copy `config/candidate-profile.example.md` to that ignored path before populating it.
3. Read every relevant material completely. Load and follow the dedicated PDF, document, spreadsheet, or other file skill when the format requires it; visually inspect scanned or image-only pages when text extraction is incomplete.
4. Extract only explicit, application-relevant facts: identity and contact details; professional URLs; education; employment, dates, and verified achievements; skills, languages, certifications, and portfolio evidence; and the path and purpose of each authorized source file. Carry work authorization, sponsorship, clearance, location, start-date, compensation, reference, or voluntary self-identification answers into the profile only when a source states the candidate's current answer clearly and unambiguously.
5. Merge extracted facts into the profile without silently overwriting an explicit saved answer. Prefer the most recent user-supplied resume for dated employment history. Record conflicting or plausibly stale values under `Conflicts requiring confirmation` and ask the user before using them.
6. Record every reviewed material under `Source documents`, including its task attachment name or private path, type, and purpose. If an attachment is authorized for later website upload but has no stable local path, save an unchanged copy under `private/` and record that path. Update `Profile last refreshed from materials` so later continuations can detect new inputs without rereading everything.
7. Never infer protected traits, demographic answers, disability or veteran status, citizenship, work authorization, sponsorship, clearance, relocation willingness, or other sensitive answers from names, photos, locations, schools, employers, or indirect context. Never store passwords, authentication data, government identifiers, financial-account data, or unrelated medical details in the profile.
8. Populate `Answers still requiring candidate direction` only with application-relevant questions that remain unsupported, ambiguous, or require a personal choice after all materials have been reviewed.

## Persist candidate responses autonomously

Treat every explicit, application-relevant response from the candidate as durable private-profile input, whether it arrives during preflight, while resolving a form-specific blocker, in a later continuation, or through text transcribed from an image.

- Update `private/candidate-profile.md` in the same turn as soon as the response is provided, before using it in a form or resuming browser work. Do this autonomously; do not wait for a separate request to remember or save the answer.
- Store reusable facts and directions in the appropriate profile section, including identity, contact, education, employment, skills, work authorization, sponsorship, start date, compensation, location, travel, screening consent, references, offers, and voluntary self-identification answers.
- Remove resolved entries from `Answers still requiring candidate direction`. If the candidate explicitly changes an earlier answer, replace the saved value and use the newest direct response going forward.
- Preserve application-specific prose only when the candidate supplied it as a reusable answer or direction. Do not turn agent-generated, role-tailored essays into candidate facts.
- Save only the supported fact transcribed from a screenshot or temporary attachment unless the candidate also designated the file as a reusable application document.
- Keep the profile and supporting materials under the ignored `private/` path. Never store passwords, one-time codes, authentication tokens, government identifiers, financial-account data, or unrelated medical details.

## Prompt for candidate direction

After the material pass, inspect `Answers still requiring candidate direction` in `private/candidate-profile.md` and identify goal-specific ambiguity. If anything remains unresolved, ask the user once in a consolidated message before taking browser action.

Before asking any candidate question, perform a source-first answer check:

- Search `private/candidate-profile.md`, current task attachments, authorized materials under `private/`, and the profile's recorded source documents for a direct, unambiguous answer to that specific question. Read the relevant source completely when a partial search result lacks necessary context.
- If the materials answer the question, save the supported response under **Persist candidate responses autonomously** and use it without asking the candidate. Ask only after the relevant materials have been exhausted and the answer remains missing, ambiguous, conflicting, plausibly stale, or requires a personal choice.
- Repeat this source-first check when a new required question appears inside an application form; do not treat a browser-form question as automatically requiring user interruption.

Ask only missing items, using this structure as applicable:

1. What full street address and postal code should applications use?
2. What is the earliest exact start date?
3. What compensation answer should be used: a target/range, negotiable, or decline to state?
4. What locations, remote arrangements, relocation, and travel are acceptable?
5. What security-clearance, export-control, background-check, and drug-screen answers may be given?
6. For voluntary demographic questions not already answered, should the agent provide specified answers or select **Decline to answer**?
7. May personal references be provided, and if so, what are their details?
8. Does the current goal need any narrower role, seniority, company, industry, or application-date criteria?

- Explain that the user may answer `decline` or `leave unanswered` for any item; then skip applications that require that unresolved answer.
- Follow **Persist candidate responses autonomously** for every new answer: save it immediately in `private/candidate-profile.md`, remove resolved items from the outstanding list, and record explicitly declined items so future runs do not ask again.
- Do not infer an answer from indirect cues in the materials, location, browser profile, Handshake preferences, or prior form autofill. Carry a value from a reviewed source only when it is explicit and unambiguous.
- Do not re-ask a resolved or declined question unless the user changes it, it is plausibly stale, or a goal introduces a materially different requirement.
- If a new required question remains unresolved after the source-first answer check, block that job, continue with alternatives, and aggregate newly discovered questions for the user.

## Launch Chrome and select sites

1. Load and follow the available Chrome-capable browser-control skill before browser work. When `control-in-app-browser` is the available skill, follow its explicit Chrome selection path and obtain the `extension` browser binding.
2. Require the Chrome plugin to be enabled, the extension to be installed in the active Chrome profile, and the extension status to be **Connected**. If Chrome control is unavailable, ask the user to complete that setup; do not fall back to the built-in browser, raw HTTP, standalone Playwright, a search connector, or Computer Use.
3. Attempt the normal Chrome browser-client initialization first. Only if it fails with the exact error `Cannot redefine property: process` and the active Chrome plugin manifest reports version `26.707.71524`, read and follow `references/chrome-26.707.71524-process-workaround.md` completely. This is a version-specific, session-only workaround; never apply it proactively, for another error, or to another plugin version.
4. Launch a distinct persistent Chrome extension binding for the run, give the task or tab group a descriptive name, and reuse that binding across goal continuations.
5. Reuse or claim a matching open Chrome tab before creating a duplicate. Open the enabled site's `start_url` when no matching tab exists. Use the profile's existing signed-in session and never inspect or store credentials, cookies, local storage, passwords, or authentication tokens.
6. Use enabled sites in `config/job-sites.json` for discovery, further restricted by the active goal. When the goal does not name a discovery source, use enabled sites by ascending `priority`; Handshake is the primary source. A verified external employer careers site or ATS reached while applying does not need its own discovery-site entry when the source configuration enables external application sites.
7. Read the site's referenced instructions before interacting. For Handshake, read `references/handshake.md` completely.
8. If the Chrome profile is signed out, ask the user to sign in in Chrome and tell you when it is ready. Do not switch browsers to bypass authentication.
9. If a local file upload is blocked, ask the user to open **Chrome > Extensions > Manage Extensions**, select the Codex extension's **Details**, enable **Allow access to file URLs**, and then restart the Chrome task. Do not switch to the built-in browser, which cannot automate file uploads.
10. Treat a goal that explicitly directs `$apply-to-jobs` to submit applications from a configured discovery source as authorization for ordinary application uploads and submissions both on that source and on verified external employer career or ATS sites used by those applications. The user has separately authorized uploading files they provide to matching job-application forms. Without an explicit submission goal, research may continue but stop before transmitting private data or submitting.

## Find eligible roles

- Follow role, seniority, location, freshness, compensation, company, and discovery-source criteria stated in the goal.
- Source roles primarily from Handshake. When `external_application_sites.enabled` is true, follow Handshake's job-specific **Apply**, employer website, or ATS links and navigate within the resulting official application site as needed to complete that position.
- If an external link lands on an employer careers homepage or search page, locate only the same position using the Handshake company, title, location, or job identifier. Do not substitute another role or use an unrelated external job board unless the goal separately authorizes that discovery source.
- If the goal contains only a count, derive role families and seniority from the private profile and resume. Do not hardcode one candidate's background into the skill.
- Verify that each source posting is still open. On every external site, verify HTTPS, employer identity, title, location, and job identifier when present before transmitting data. Stop on mismatches, impersonation signals, payment requests, or requests for credentials or sensitive financial data unrelated to a normal application.
- Compare start dates, graduation timing, work authorization, sponsorship, citizenship, and clearance requirements with the exact private-profile values. Skip conflicts and do not expose those values in logs or public artifacts.
- Do not treat a location as proof of relocation willingness. Skip a role when a required location, travel, or relocation answer cannot be made from the goal or profile.
- Before opening a form, check for a prior submission:

  ```bash
  python3 .agents/skills/apply-to-jobs/scripts/tracker.py check \
    --url "https://employer.example/jobs/123" \
    --company "Example" \
    --title "Data Scientist"
  ```

## Complete each application

Use the Chrome extension for discovery, form completion, uploads, redirects, and confirmation checks. Follow the selected Chrome binding's documentation for snapshots, locators, confirmations, and tab cleanup. Do not substitute the built-in browser, Computer Use, or standalone browser automation.

For each application:

1. Verify the company, title, location, posting status, core qualifications, work-authorization language, and application URL.
2. Fill only facts supported by the profile or source documents. Use the resume's dated employment history when sources conflict.
3. Answer work-authorization, immigration, sponsorship, citizenship, and clearance questions exactly as saved in the private profile. If a required value is missing or ambiguous, perform the source-first answer check before blocking the application or asking the user; never infer it.
4. Answer voluntary self-identification questions only when the private profile contains the user's explicit answer or instruction to decline. Do not infer demographic information.
5. Tailor short written responses and cover-letter text to the role using only supported facts. Do not invent metrics, titles, dates, technologies, motivations, referrals, or personal stories.
6. Upload relevant files supplied by the user through the Chrome extension without asking for upload permission again during an active submission goal. Inspect each file locally first, verify the company and role destination, and upload it only to a matching job-application form. Use the resume listed in the private profile by default; resolve document conflicts according to the private profile; upload cover letters, transcripts, or other files only when relevant. Do not upload these files to resume optimizers, public profiles, recruiter messages, or unrelated services.
7. Review every answer before submission. Correct autofill errors, especially legal name, dates, degree names, sponsorship, phone number, and email.
8. Submit when all required answers are supported and the form shows no unresolved error.
9. Confirm success from the final page, confirmation number, or confirmation email. A click on **Submit** without confirmation does not count.
10. Record the result immediately. A submitted record requires confirmation evidence:

   ```bash
   python3 .agents/skills/apply-to-jobs/scripts/tracker.py record \
     --status submitted \
     --site "Handshake" \
     --company "Example" \
     --title "Data Scientist" \
     --url "https://employer.example/jobs/123" \
     --confirmation "Application submitted page displayed"
   ```

## Handle blockers without losing momentum

- Never bypass a CAPTCHA, MFA challenge, anti-bot control, queue, rate limit, or site security measure. Ask whether the user wants to solve a displayed CAPTCHA and continue only after explicit confirmation.
- Do not take timed assessments, coding tests, recorded interviews, or personality tests unless the goal explicitly includes them.
- Accept ordinary privacy notices, truthful-application certifications, and electronic-signature acknowledgements needed for submission. Stop on unusual releases, arbitration choices, financial commitments, or terms unrelated to a normal job application.
- When a required answer remains unknown after the source-first answer check, or a site needs user interaction, record the job as `blocked`, include a concise reason, and continue to another eligible role.
- Record clearly ineligible, closed, duplicate, or poor-fit roles as `skipped` when retaining that history will prevent repeated work.
- Aggregate questions and blockers for the user instead of interrupting after every job. Continue while other eligible applications remain.

Examples:

```bash
python3 .agents/skills/apply-to-jobs/scripts/tracker.py record \
  --status blocked --site "Handshake" --company "Example" --title "Analyst" \
  --url "https://employer.example/jobs/456" \
  --note "Street address is required"

python3 .agents/skills/apply-to-jobs/scripts/tracker.py status
```

## Finish exactly at the target

- Count only tracker records whose status is `submitted` in the current run.
- Re-check tracker status before each new submission and stop when `remaining` is zero.
- Report the confirmed application count, source site, companies and roles submitted, and any unresolved blockers without exposing private form data.
- When the target is reached and goal tools are available, call `update_goal` with `status: complete`.
- Mark the goal blocked only after the same blocking condition has persisted for at least three consecutive goal turns, no eligible alternative remains, and user input or an external state change is required.
- If the user pauses or clears `/goal`, stop applying. Do not turn a job-application goal into an unbounded scheduled task.

The tracker writes private state to `private/application-state.json` by default. Keep that file and all candidate documents out of version control.
