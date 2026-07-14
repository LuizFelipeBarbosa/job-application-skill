# Apply to Jobs

`apply-to-jobs` is a Codex skill that searches for matching jobs and submits a
user-defined number of applications through Handshake and verified employer or
ATS sites. It uses the user's signed-in Chrome session, checks for duplicate
applications, and records only submissions with confirmation evidence.

## Recommended model

For the most reliable browser navigation and application review, use
`gpt-5.6-terra` with reasoning effort set to `high`, if that model is available
to you. Simpler models may also work, especially for straightforward forms, but
may require closer supervision.

## Requirements

- Codex with repository skills enabled
- The Codex Chrome plugin and extension, connected to the Chrome profile you
  use for job applications
- A signed-in Handshake account
- Python 3 for the local application tracker
- A resume and the candidate information required by application forms

The skill uses the existing browser session. Do not place passwords, cookies,
authentication tokens, or other credentials in this repository.

## Install

Clone the repository and start Codex from its root:

```bash
git clone https://github.com/LuizFelipeBarbosa/job-application-skill.git
cd job-application-skill
```

Codex discovers the repo-scoped skill under
`.agents/skills/apply-to-jobs/`. Clone the whole repository rather than copying
only the skill directory because the workflow also uses the generic files under
`config/` and creates private state at the repository root.

## Configure

Create your private candidate profile from the provided template:

```bash
mkdir -p private/documents
cp config/candidate-profile.example.md private/candidate-profile.md
```

Then:

1. Fill in `private/candidate-profile.md` with truthful candidate information
   and application preferences.
2. Put authorized resumes, cover letters, transcripts, or other application
   files in `private/documents/` and list their paths in the profile.
3. Review `config/job-sites.json`. Handshake is enabled as the primary discovery
   source by default.
4. Connect the Codex Chrome extension to the Chrome profile that is signed in
   to the job sites you want to use.

The entire `private/` directory, application history, candidate profiles,
resumes, cover letters, transcripts, and generated output are ignored by Git.
Keep real candidate data out of `config/candidate-profile.example.md` and other
tracked files.

## Use

Start a goal with an explicit number of applications and selection criteria:

```text
/goal Apply to 10 entry-level data science jobs using $apply-to-jobs.
```

The skill first asks for any missing candidate direction. It then searches the
configured sources, skips duplicate or incompatible roles, completes supported
answers, and continues until it reaches the requested number of confirmed
submissions or encounters a genuine blocker.

You can make the goal more specific:

```text
/goal Apply to 5 new-grad software engineering jobs in California or remote,
posted within the last 14 days, using $apply-to-jobs.
```

Review the candidate profile carefully before beginning. Job applications are
external submissions made in your name, so stay available for questions and
monitor the run when forms contain unusual or sensitive requests.

## Repository layout

```text
.agents/skills/apply-to-jobs/
  SKILL.md                 Workflow and safety instructions
  agents/openai.yaml       Codex skill metadata
  references/              Site-specific operating guidance
  scripts/tracker.py       Private duplicate and submission tracker
config/
  candidate-profile.example.md
  job-sites.json
private/                   Local candidate data; never committed
```

Job sites and browser interfaces change over time. Re-check the workflow and
site-specific instructions before relying on the skill for unattended batches.
