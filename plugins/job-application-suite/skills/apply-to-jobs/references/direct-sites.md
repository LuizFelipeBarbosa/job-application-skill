# Direct and user-named job sites

Use this workflow when the user supplies an exact posting URL or names a site that is not a persistent discovery source in `config/job-sites.json`.

## Select and verify the posting

1. Treat the user's exact URL or named site as the selected source for this run. Do not silently fall back to Handshake or a different job board.
2. For an exact URL, open it directly. For a named site, use its own job search with the run criteria and open a matching detail page.
3. Verify HTTPS, employer, title, location, posting status, and any stable job or requisition identifier. If the site redirects to an employer career site or ATS, confirm that it is the same position before continuing.
4. Stop on a general careers page when the same position cannot be found. Never substitute another opening without applying the run's normal discovery and reservation checks.

## Browser permission scope

Use the user's signed-in Chrome profile and the current browser binding. Keep global all-sites access disabled. If the selected host is not already allowed, request only the narrow host access required by the active browser surface. A one-off source does not require editing persistent job-site configuration.

After verification, use the core skill's duplicate check, reservation, answer resolution, account creation, attachment, submission, and confirmation workflows.
