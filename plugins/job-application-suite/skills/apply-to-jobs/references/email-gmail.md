# Gmail verification adapter

Use Gmail only for profile validation, narrow search, and reading the single selected verification or confirmation message.

## Allowed operations

- Read the connected Gmail profile when an external preflight is explicitly requested.
- Search message IDs with a query constrained by the recorded request time, application recipient, and verified employer or ATS identity.
- Read only the selected message or its thread when the selection contract requires it.

Do not call Gmail tools that send, draft, forward, archive, delete, trash, label, mark, or otherwise mutate mail. Do not browse the inbox, list unrelated threads, or expand the query when a narrow search returns no match.

## Query construction

Start from all available constraints: `after:<unix-seconds>`, `to:<application-email>`, `from:<verified-sender-or-domain>` when known, and a quoted employer, ATS, role, or verification term. Search IDs first. Read content only after `email-verification.md` identifies one unambiguous candidate.

For submission confirmations, require the employer, ATS, role, or requisition identity and a receipt time after submission. A message received before the recorded submission attempt cannot confirm success.
