# Handshake application workflow

Use this guide when `Handshake` is enabled in `config/job-sites.json` or named in the active goal.

## Launch and scope

1. Launch a distinct persistent Chrome extension binding and name its task or tab group for the application run.
2. Reuse or claim an existing Handshake tab in the active Chrome profile when available; otherwise open `https://app.joinhandshake.com/explore`.
3. Use the profile's existing signed-in session. If Handshake shows a sign-in page, ask the user to sign in in Chrome and tell you when it is ready. Do not inspect or store credentials, cookies, or session data.
4. Use Handshake as the primary discovery source. When `external_application_sites.enabled` is true, use Handshake-hosted forms or continue to verified external application sites for the same position.
5. Follow job-specific **Apply**, employer website, or ATS links from Handshake. If the link opens a new tab, keep the Handshake job tab for provenance and control the new tab through the same Chrome extension binding.
6. Allow official employer career sites, employer-authorized ATS platforms, and any job-specific external destination needed to apply to the same verified position. Do not use an external job board to discover unrelated positions when `allow_external_job_boards_as_discovery` is false.

## Search jobs

- Navigate to the **Jobs** link at `/job-search` or the configured `job_search_url`.
- Apply the goal's query, job type, location, and other eligibility filters. The live search UI exposes **Describe a job you want**, **Location**, job-type controls, **Filters**, and **Sort by**.
- Prefer `posted_date_desc` when freshness is not otherwise specified.
- Run focused searches for one role family at a time. Do not use Handshake's saved interests, recommendations, or current selected job as a substitute for the goal criteria.
- Treat `/job-search/<job-id>` as the stable Handshake job identity. Ignore search, pagination, location, and recommendation query parameters when checking duplicates.

## Evaluate a job

Read the detail view before applying. Verify:

- employer and title;
- employment type, location, pay when present, posting age, deadline, and expected dates;
- description, minimum qualifications, and application requirements;
- work-authorization, citizenship, sponsorship, and clearance language; and
- whether Handshake says the candidate matches, while independently verifying the actual requirements.

Do not rely on Handshake's match indicator alone. Skip jobs that conflict with the active goal or the candidate's saved work-authorization facts.

## Apply

1. Locate **Apply** from a fresh page snapshot and scope it to the job-detail area. Handshake can render more than one Apply control; do not use positional shortcuts. Confirm the chosen locator resolves uniquely.
2. Select **Apply** and inspect the resulting state.
   - For a Handshake-hosted form, review the selected resume, attachments, profile fields, and questions before submission.
   - For an external employer or ATS site, verify HTTPS, employer, title, location, and job identifier when available, then continue through all application pages with the same Chrome extension binding.
   - If the external link reaches a careers homepage or search page, search only for the exact Handshake position. Stop if the position cannot be verified; do not replace it with a different opening.
3. Upload relevant files through the Chrome extension under the standing permission in `private/candidate-profile.md`. Use only paths and restrictions recorded in that profile. Upload transcripts only when academic records are required, and follow the profile's restrictions for sensitive identifiers. If Chrome cannot access a local file, ask the user to enable **Allow access to file URLs** for the Codex extension and restart the Chrome task; do not switch to the built-in browser.
4. Treat an active goal that explicitly says to apply from Handshake using `$apply-to-jobs` as authorization to transmit saved application data and submit ordinary applications both on Handshake and on verified external employer or ATS destinations for those roles. Without that explicit submission goal, stop before the first upload or final submission and ask.
5. After submitting, verify a success page, confirmation number, or confirmation email. Record the stable Handshake job URL with `--site "Handshake"`; when the final form is external, include the external application host and URL in the tracker note.

## Leave unrelated Handshake state unchanged

Do not, unless the goal explicitly asks:

- reply to recruiters or open Inbox conversations;
- modify the Handshake profile, career interests, saved searches, or job preferences;
- upload the resume to Sidekick or use **Optimize resume**;
- save or hide jobs;
- complete profile prompts; or
- interact with Feed, AI showcase, Events, People, Employers, notifications, or school resources.

If Handshake presents a CAPTCHA, ask whether the user wants to solve it and continue only after explicit confirmation. Never bypass an anti-bot or security control.
