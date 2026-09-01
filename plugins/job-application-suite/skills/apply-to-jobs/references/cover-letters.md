# Required cover-letter workflow

Read this guide only when the live application requires a cover letter.

## Delegate a focused writer

When subagents are available, give one cover-letter subagent a bounded, read-heavy and document-creation task. Provide:

- the verified employer, role, location, job identifier, posting text, and posting URL;
- the current candidate-profile snapshot and authorized resume or supporting-document paths;
- the form's accepted file types and any stated length or content requirements; and
- a unique output path under `<workspace>/private/documents/tailored/`.

The subagent may research the employer and role and create the document. It must not operate the application form, mailbox, credential vault, clipboard, tracker, or candidate profile. It must use the dedicated document or PDF skill required by the output format, render and visually verify the final artifact, and return only the output path, SHA-256 signature, non-sensitive source URLs, and a concise statement of the candidate evidence used.

If subagents are unavailable, perform the same research and document workflow in the coordinator.

## Research and draft truthfully

1. Use the live posting and official employer sources first. Supplement with current reliable sources only when official material is insufficient, and verify that every source refers to the same employer and role.
2. Compare the posting's responsibilities and qualifications with supported candidate experience, skills, education, projects, and stated goals. Select the strongest relevant evidence rather than summarizing the entire resume.
3. Write a concise, role-specific letter in the candidate's established professional voice. Do not invent metrics, experiences, product use, referrals, personal stories, or longstanding enthusiasm.
4. Address the employer and role correctly. Use a neutral salutation when no verified recipient is available.

## Build and hand off the artifact

Create the file type accepted by the form; prefer a polished one-page PDF when PDF is accepted. Use a filename that identifies the employer and role without exposing unnecessary personal data. Verify the rendered pages for clipping, overflow, missing glyphs, accidental placeholders, and incorrect employer or role references.

Before upload, the coordinator must compare the artifact with the live form and posting, confirm its path and signature, and inspect the rendered result. Upload only that verified artifact. Do not merge agent-authored cover-letter prose into durable candidate facts.
