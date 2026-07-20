# Manual beta acceptance

Complete separate dated records on macOS and Windows. Use synthetic data except for the final user-authorized canary. Never commit candidate data, credentials, codes, tokens, or message bodies; record only pass/fail, versions, and non-sensitive confirmation evidence.

## macOS record

- [ ] Fresh-clone plugin installation and doctor exit `0`
- [ ] Temporary credential generate, copy, guarded clear, and delete with cleanup verified
- [ ] Gmail profile check and one user-created synthetic verification message selected correctly
- [ ] Chrome and Computer Use complete the local diagnostic fixture, including synthetic upload
- [ ] One review-before-submit, user-authorized application canary with visible confirmation
- [ ] Tester, macOS version, Codex version, Chrome version, date, and evidence reference recorded

## Windows record

- [ ] Fresh-clone plugin installation and doctor exit `0`
- [ ] Temporary credential generate, copy, guarded clear, and delete with cleanup verified
- [ ] Gmail profile check and one user-created synthetic verification message selected correctly
- [ ] Chrome and Computer Use complete the local diagnostic fixture, including synthetic upload
- [ ] One review-before-submit, user-authorized application canary with visible confirmation
- [ ] Tester, Windows version, Codex version, Chrome version, date, and evidence reference recorded

## Release gate

Publish `v0.1.0-beta.1` only when all automated checks pass, both records above are complete, `scripts/validate_release.py` reports no deployment state, and both production dependency audits report no known vulnerabilities.
