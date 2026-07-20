# Handshake application workflow

Use this guide when `Handshake` is enabled in `config/job-sites.json` or named in the active run request. Follow the core skill and `references/browser.md` for global authorization, upload, confirmation, and human-verification rules.

## Launch and scope

1. Reuse or claim an existing Handshake tab in the active Chrome profile when available; otherwise open the configured `start_url`.
2. Treat Handshake as one configured discovery source, not as an implicit requirement. When `external_application_sites.enabled` is true, use Handshake-hosted forms or continue to a verified external application site for the same position.
3. Follow job-specific **Apply**, employer website, or ATS links from Handshake. If the link opens a new tab, keep the Handshake job tab for provenance and control the new tab through the same browser binding.
4. Allow official employer career sites, employer-authorized ATS platforms, and any job-specific external destination needed to apply to the same verified position. Do not use an external job board to discover unrelated positions when `allow_external_job_boards_as_discovery` is false.

## Search jobs

- Navigate to the **Jobs** link at `/job-search` or the configured `job_search_url`.
- Apply the run's query, job type, location, and other eligibility filters. The live search UI exposes **Describe a job you want**, **Location**, job-type controls, **Filters**, and **Sort by**.
- Prefer `posted_date_desc` when freshness is not otherwise specified.
- Run focused searches for one role family at a time. Do not use Handshake's saved interests, recommendations, or current selected job as a substitute for the run criteria.
- Treat `/job-search/<job-id>` and `/jobs/<job-id>` as the same stable Handshake identity. Extract `<job-id>` before reservation and ignore search, pagination, location, and recommendation query parameters when checking duplicates.

## Evaluate a job

Read the detail view before applying. Verify:

- employer and title;
- employment type, location, pay when present, posting age, deadline, and expected dates;
- description, minimum qualifications, and application requirements;
- work-authorization, citizenship, sponsorship, and clearance language; and
- whether Handshake says the candidate matches, while independently verifying the actual requirements.

Do not rely on Handshake's match indicator alone. Skip jobs that conflict with the run or the candidate's saved eligibility facts.

## Apply

1. Locate **Apply** from a fresh page snapshot and scope it to the job-detail area. Handshake can render more than one Apply control; do not use positional shortcuts. Confirm the chosen locator resolves uniquely.
2. Select **Apply** and inspect the resulting state.
   - For a Handshake-hosted form, review the selected resume, attachments, profile fields, and questions before submission.
   - For an external employer or ATS site, verify HTTPS, employer, title, location, and job identifier when available, then continue through all application pages with the same Chrome extension binding.
   - If the external link reaches a careers homepage or search page, search only for the exact Handshake position. Stop if the position cannot be verified; do not replace it with a different opening.
3. Follow `references/browser.md` for document selection and uploads. Upload transcripts only when academic records are required and the profile permits their use.
4. After submitting, verify a success page or confirmation number. Record the stable Handshake job ID and URL with `--site "Handshake"`; when the final form is external, include its host and URL in the tracker note.
5. Before external data entry and again before final submission, update the same lifecycle with the verified employer ATS URL or requisition ID and rerun the duplicate check against that final identity.

## Leave unrelated Handshake state unchanged

Do not, unless the goal explicitly asks:

- reply to recruiters or open Inbox conversations;
- modify the Handshake profile, career interests, saved searches, or job preferences;
- upload the resume to Sidekick or use **Optimize resume**;
- save or hide jobs;
- complete profile prompts; or
- interact with Feed, AI showcase, Events, People, Employers, notifications, or school resources.

Follow the core blocker workflow when Handshake presents a CAPTCHA, assessment, missing-answer requirement, or site error.
