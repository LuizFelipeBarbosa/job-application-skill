# Candidate profile workflow

Use this guide whenever creating, refreshing, or consulting the private candidate profile.

## Create or locate the profile

Treat `<workspace>/private/candidate-profile.md` as durable, private application memory. If it does not exist, copy `<skill-root>/assets/candidate-profile.md` to that path and populate it from authorized materials. Keep the profile and all candidate documents out of version control.

On first use, tell the user once:

> I will save reusable application answers locally under `private/` so I do not ask again. Label any answer `session only` if you do not want it retained.

Honor a saved retention preference on later runs without repeating the notice. Use a session-only answer for the current run or form, but do not write it to the profile or update history.

## Refresh from authorized materials

1. Inventory current task attachments, candidate materials intentionally placed under `private/`, and files already listed under `Source documents`. Do not scan unrelated workspace files.
2. Include resumes or CVs, cover letters, transcripts, portfolios, certificates, professional-profile exports, and reusable prior application answers.
3. Read each new or modified relevant source completely. Load the dedicated PDF, document, spreadsheet, or image skill when its format requires it.
4. Record each reviewed source's task attachment name or private path, type, purpose, and a stable last-reviewed signature such as SHA-256 or modification time plus size. Reuse the recorded extraction when the signature has not changed.
5. If an authorized upload has no stable path, save an unchanged copy under `private/` and record its path.

## Extract and merge facts

- Extract only explicit application-relevant facts: identity and contact information, professional URLs, education, employment, dated achievements, skills, languages, certifications, and portfolio evidence.
- Carry work authorization, sponsorship, citizenship, clearance, location, start-date, compensation, reference, screening, or voluntary self-identification answers only when the source states the candidate's current answer directly and unambiguously.
- Prefer the newest user-supplied resume for dated employment history. Do not silently overwrite a direct saved answer. Record conflicting or plausibly stale values under `Conflicts requiring confirmation` and do not use them until resolved.
- Never infer protected traits, demographic answers, disability or veteran status, citizenship, work authorization, sponsorship, clearance, relocation willingness, or sensitive answers from names, photos, schools, employers, locations, browser autofill, or indirect context.
- Never store passwords, one-time codes, or authentication data in the candidate profile or any file. Store a password only in the operating-system credential vault through `scripts/password_manager.py` when the bounded application run's standing account-creation authorization applies or the user separately authorizes the account. Never store government identifiers, financial-account data, or unrelated medical details.

## Persist explicit answers

- Save a reusable explicit answer in the same turn before using it in a form. Update `Profile last updated`, append a concise dated entry to `Update history`, and remove any resolved outstanding question.
- Store facts in the closest existing section. Use `Additional reusable application information` rather than forcing an answer into an unrelated field.
- Preserve an explicitly changed answer as the newest value. Do not re-ask a resolved or declined question unless the user changes it, it becomes plausibly stale, or the new run materially changes its meaning.
- Store voluntary self-identification details only when the user explicitly provides them as reusable. A standing direction to decline may be stored without storing the underlying trait.
- Preserve application-specific prose only when the user supplied it as a reusable answer. Do not save agent-generated tailored essays as candidate facts.
- During a subagent-driven run, let only the coordinator write the candidate profile. Have workers read the current profile snapshot and report newly supplied answers or conflicts to the coordinator for reconciliation.
- Before completing a run, reconcile explicit user responses and new or modified authorized sources that are not yet represented in the profile.

## Resolve answers automatically and ask last

Before asking any question, attempt to answer it automatically in this order:

1. Apply current user directions and direct, reusable saved answers.
2. Search the profile and relevant authorized candidate sources for direct supporting facts. Read the necessary context rather than relying on an isolated text match.
3. Derive an answer conservatively when the materials make it unambiguous. Calculate dates or years without rounding upward or double-counting overlaps; evaluate a qualification only against documented evidence; choose the least inflated supported proficiency or responsibility level.
4. Use the live posting and form context to interpret what the employer is asking.
5. For company-, role-, team-, product-, mission-, values-, or motivation-related questions, research the employer and role. Prefer the posting and official company pages, then current reliable sources when official material is insufficient. Verify the entity and paraphrase rather than copying.
6. Compose concise role-specific prose by connecting verified employer facts to supported candidate experience, skills, projects, and stated goals. Express evidence-backed interest in the opportunity without inventing longstanding enthusiasm, firsthand product use, referrals, personal anecdotes, or candidate facts.

An answer does not need to appear verbatim in a source when it follows reliably from supported facts. For example, calculate a conservative experience duration from documented dates, answer a minimum-qualification question from documented education or skills, and draft **Why this company?** from verified company work plus the candidate's relevant background. Company research may support employer context and prose, but never use it to manufacture candidate credentials, experiences, preferences, or sensitive personal facts.

For a missing optional answer, leave the field blank or use a neutral **Prefer not to answer** or **Decline** option when the form allows it. Never infer protected traits, legal status, work authorization, sponsorship, citizenship, clearance, voluntary self-identification, or other sensitive answers. Do not infer material personal commitments such as relocation, travel, start date, or compensation unless authorized candidate materials or saved user directions directly support the response.

Ask before discovery only when the answer materially determines a useful search, such as an otherwise unknown role family, location boundary, work arrangement, or essential eligibility constraint. Ask during an application only when the live form requires the answer and no supported value exists.

Do not collect these merely as preflight questions:

- full street address;
- exact start date;
- compensation response;
- relocation, travel, screening, or clearance details;
- voluntary demographic choices; or
- personal references.

When one is required, ask the exact form question, explain that the user may answer, decline, leave it unanswered, or mark the answer `session only`, then resume the form or skip only that application as appropriate.
