# Job Applications

A single agent skill, `apply-to-jobs`, that mass-applies to jobs on my behalf. It runs under both Codex (Chrome plugin + Gmail connector) and Claude Code (Claude in Chrome + Gmail MCP) from the same `SKILL.md`.

Given "apply to 10 data science jobs on Handshake", it searches, checks fit against `private/profile.md`, writes a tailored resume and cover letter per job in my house style, creates ATS accounts and reads Gmail verification codes when needed, submits, and logs everything under `private/`. It does not ask permission per job; it skips what it cannot answer truthfully and reports those at the end.

## Layout

```
skills/apply-to-jobs/     the skill (SKILL.md, references/, scripts/, assets/)
.claude/skills/           symlink -> skills/apply-to-jobs   (Claude Code discovery)
.agents/skills/           symlink -> skills/apply-to-jobs   (Codex discovery)
private/                  gitignored personal data
  profile.md              facts, standard answers, targets, never-do list
  resume.md               resume source, rendered per job
  documents/              Resume.pdf, Transcript.pdf, WritingSample.pdf, samples/*.md
  applications.json       the log (jobs.py)
  applications/<id>/      job.md, resume.pdf, cover_letter.pdf, answers.md per application
  accounts.json           [{host, email, created}]; passwords are in the macOS Keychain
  archive/                history from earlier versions of this skill
```

## Setup (once)

1. `uv` installed (`brew install uv`). Scripts declare their own dependencies and run with `uv run`.
2. Sign in to Handshake in Chrome. Connect Gmail in Codex (connector) or Claude Code (`/mcp`).
3. Fill `private/profile.md` and `private/resume.md` (templates in `skills/apply-to-jobs/assets/`).

## Run

In Codex: `$apply-to-jobs apply to 10 quant and data science jobs on Handshake`.
In Claude Code: `/apply-to-jobs apply to 10 quant and data science jobs on Handshake`.

Check progress any time:

```bash
uv run skills/apply-to-jobs/scripts/jobs.py status
uv run skills/apply-to-jobs/scripts/jobs.py list --status needs_input
uv run skills/apply-to-jobs/scripts/jobs.py report
```

Render documents by hand:

```bash
uv run skills/apply-to-jobs/scripts/render_resume.py --in private/resume.md --out out.pdf --png
uv run skills/apply-to-jobs/scripts/render_cover_letter.py --in letter.md --out out.pdf --png
```
