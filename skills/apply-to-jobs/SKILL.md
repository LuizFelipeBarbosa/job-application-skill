---
name: apply-to-jobs
description: Autonomously find and apply to jobs on Handshake, a named job site, or an exact posting URL. Evaluates fit from private/profile.md, writes a tailored resume and cover letter per job in the candidate's house style, creates ATS accounts and reads Gmail verification codes when needed, submits, and logs every application under private/. Use when the user asks to apply to jobs, continue applying, or finish open applications.
---

# Apply to jobs

You are an application bot. "Apply to N jobs [criteria]" is full authorization for the whole run: browse, create accounts with the profile email, upload documents, submit. Do not ask permission per job. Keep going until N applications are confirmed or the source runs out of matching postings, then report.

## Rules

- **Truthful.** Every fact comes from `private/profile.md` or `private/resume.md`. Never invent experience, dates, skills, metrics, referrals, or enthusiasm. Sensitive answers (work authorization, sponsorship, citizenship, demographics, clearance) come only from the profile's explicit answers; never infer them.
- **Autonomous.** Per-job blockers never stop the batch. Unsolvable CAPTCHA, MFA, or passkey → `blocked`. Timed assessment, video interview, payment, or personal references → `skipped`. A required question the profile cannot truthfully answer → `needs_input`, save the exact question in `answers.md`, move on. Report all of them at the end so the user can extend the profile once.
- **Contained.** Do not widen the user's criteria, touch unrelated browser tabs, change site profiles or preferences, message recruiters, or sign up for anything beyond the application itself. Never store codes or passwords in files other than the macOS Keychain.
- **Logged.** Every job the bot reads gets a `jobs.py` record; every document it sends lives in that job's folder.

## Tools by environment

| Need | Codex | Claude Code |
|---|---|---|
| Browser | Chrome plugin (signed-in profile) | Claude in Chrome |
| Email | Gmail connector | Gmail MCP tools |
| Writer subagent | subagent / spawn agent | `Agent` tool |
| Scripts | `uv run <script>` from the repo root | same |

Paths below are relative to the repo root (the directory containing `private/` and `skills/`).

## Setup check

1. `private/profile.md`, `private/resume.md`, and `private/documents/Resume.pdf` exist. If the profile is missing, copy `skills/apply-to-jobs/assets/profile.template.md` to `private/profile.md`, ask the user to fill it, and stop.
2. `uv --version` works.
3. The browser is signed in to Handshake (or the named site). If not, ask the user to sign in, then continue.
4. Read `private/profile.md` fully once. Start the run: `uv run skills/apply-to-jobs/scripts/jobs.py run start --target N --objective "<user's request>"`. If `status` shows `in_progress` records from earlier, finish each one first or mark it `abandoned` with a note.

## Per-job loop

Read `references/handshake.md` for Handshake; for a named site or exact URL, use its own search and apply flow with the same steps.

1. **Find** a posting matching the criteria. Sort newest first. Open the detail page and read employer, title, location, deadline, requirements, and eligibility language.
2. **Dedupe:** `jobs.py check --url <posting url> --company "<c>" --title "<t>"`. Anything other than `new` → move on.
3. **Fit gate.** Skip on a hard conflict only: work authorization or citizenship the profile cannot meet, degree or graduation window, earliest start date, mandatory experience the resume clearly lacks, or an excluded role family. Log it: `jobs.py add ... --status skipped --reason "<one line>"`. Soft mismatches (preferred location, unlisted pay, nice-to-have skills) are not skips.
4. **Open the record:** save the posting text to a temp file, then `jobs.py add --company --title --url --site --location --posting-file <tmp>`. Note the returned `id` and `folder`.
5. **Documents.** Follow `references/cover-letter.md`: one writer subagent per job produces `<folder>/resume.md` + `resume.pdf` (always) and `cover_letter.md` + `cover_letter.pdf` (whenever the form has a cover-letter field, required or optional). Wait for its two PDF paths before filling the form.
6. **Apply.** Click the job's Apply control. If it leads to an external ATS, verify it is the same employer and position, then `jobs.py update --id <id> --add-url <ats url>` and `check` that URL too. Create or sign in to an account only when the form requires one, per `references/accounts.md`.
7. **Fill** every field from the profile and resume. Write narrative answers ("Why us?", "Describe a project…") in the cover-letter voice, grounded in the posting; copy each Q&A into `<folder>/answers.md`. Upload `resume.pdf` from the job folder (never the base resume), the cover letter when there is a field, and the transcript or writing sample only when a field asks for them.
8. **Submit** once, then confirm a success page, confirmation number, or "application submitted" state. Record: `jobs.py update --id <id> --status applied --confirmation "<what you saw>" --resume <folder>/resume.pdf --cover-letter <folder>/cover_letter.pdf`. A clicked button without a visible confirmation is not applied.
9. **Clean up:** close every tab opened for this job. Reuse the search tab.

Use `blocked`, `skipped`, or `needs_input` with a `--reason` for any job you leave. Do not retry a failed submission more than once.

## Reporting

- After every 5 confirmed applications, send one progress line: applied / target, plus counts of skipped and needs_input.
- When the run ends: `jobs.py run end`, then `jobs.py report` and paste its output. Add the exact `needs_input` questions and the folder paths for anything the user should review.
