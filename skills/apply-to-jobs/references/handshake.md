# Handshake

Base URL `https://app.joinhandshake.com`. Job search: `/job-search`. A posting's id is the number in `/job-search/<id>`, `/jobs/<id>`, or `/public/jobs/<id>`; `jobs.py` treats all three as the same job.

## Search

- Use the search box ("Describe a job you want"), **Location**, job-type controls, **Filters**, and **Sort by**. Sort by most recent unless the user says otherwise.
- Run one role family per search (for example "data scientist", then "quantitative analyst"). Paginate before changing the query.
- Ignore Handshake's "you're a match" badge, saved interests, and recommendations. Judge fit from the posting text and the profile.

## Evaluate

Read the detail pane: employer, title, employment type, location, pay if shown, posting age, deadline, description, minimum qualifications, and any work-authorization, citizenship, sponsorship, or clearance language. Apply the fit gate from SKILL.md.

## Apply

- The detail view can render more than one **Apply** control; take a fresh snapshot and click the one inside the job-detail area.
- **Hosted form:** Handshake shows a modal with resume selection, optional attachments, and questions. Upload the job-folder `resume.pdf` as a new document rather than reusing an existing Handshake document. Answer the questions, submit, and wait for "Application submitted".
- **External apply:** Handshake opens the employer site or ATS in a new tab. Keep the Handshake tab, work in the new tab, confirm HTTPS and the same employer and title, and add the ATS URL to the record. If the link lands on a generic careers page, search that site for the exact title and location; if the position is not there, mark `skipped --reason "external link did not reach posting"`.
- Confirmation on Handshake is the "Application submitted!" state; on external sites it is a thank-you page, confirmation number, or confirmation email.

## Leave alone

Do not: reply to recruiters or open Inbox; edit the Handshake profile, career interests, saved searches, or preferences; upload the resume to Sidekick or use "Optimize resume"; save, hide, or follow jobs and employers; interact with Feed, Events, People, or school resources.
