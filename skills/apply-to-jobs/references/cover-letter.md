# Tailored documents (resume + cover letter)

One writer subagent per job. It reads, writes, renders, checks, and returns only file paths. The coordinator never drafts letters itself; that keeps its context flat across the batch.

## Subagent prompt

Send this, filling the placeholders:

```
You write application documents for one job. Everything you write must be true to the source files; you may reorder, select, trim, and rephrase, never add facts.

Inputs (read all of them):
- Job posting: <folder>/job.md
- Candidate profile: private/profile.md
- Base resume (source of truth for every bullet): private/resume.md
- Voice samples: private/documents/samples/*.md
- Cover letter needed: yes | no

Produce:
1. <folder>/resume.md — a copy of private/resume.md tailored to this posting: reorder sections and entries so the most relevant come first, keep the bullets that speak to the posting's requirements, trim or tighten the rest, and reorder Skills to lead with what the posting names. Keep the exact grammar of the source file (# name, contact line, ## sections, ### heading :: date, - bullets). Do not change the name or contact line.
2. <folder>/cover_letter.md — only if a cover letter is needed. Same block format as the samples: name and contact block, today's date, salutation, four short paragraphs, closing. About 350–400 words. Paragraph 1: the exact role and where it was posted, graduation and degrees, one sentence on why this employer or practice area. Paragraphs 2–3: the two or three experiences from the resume that best match the posting's responsibilities, with the concrete numbers and tools the resume states. Paragraph 4: what you would bring, location flexibility from the profile, thank you. Use the employer's own vocabulary for the role; do not claim prior contact, product use, or long-held passion.

Then render and check:
  uv run skills/apply-to-jobs/scripts/render_resume.py --in <folder>/resume.md --out <folder>/resume.pdf --png
  uv run skills/apply-to-jobs/scripts/render_cover_letter.py --in <folder>/cover_letter.md --out <folder>/cover_letter.pdf --png
Each must report "1 page". If not, trim and re-run. Look at the PNGs and fix anything clipped, empty, or referring to the wrong employer or role.

Reply with exactly: the two PDF paths (or one), and two lines on what you emphasized. Nothing else.
```

## Voice (what the samples establish)

- First person, plain professional English, no buzzwords, no exclamation marks.
- Concrete over general: "analyzed more than 150,000 deal memos with Latent Dirichlet Allocation" beats "used machine learning".
- Salutation "Dear <Employer> Hiring Team," when no name is known. Close with "Sincerely," and the name.
- Dates written like "September 1, 2026".

## Coordinator checks before upload

Open the returned PDF paths exist, spot-check the cover letter's first paragraph for the right employer and title, then upload from the job folder. Record both paths on the `jobs.py update --status applied` call.
