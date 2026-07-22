# Job Application Suite

`job-application-suite` is an MIT-licensed Codex plugin for bounded job-application runs. The `0.1.0-beta.1` source includes duplicate-safe tracking, Gmail-assisted verification, Chrome and Computer Use guidance, OS-vault password storage, a local analytics dashboard, and an owner-only hosted dashboard.

This beta can submit applications in your name. Review the candidate profile, platform limitations, and run brief before allowing external data entry.

## Requirements

- Python 3.9–3.13
- uv 0.9.29 or newer
- Node.js 22.13 or newer
- pnpm 10.28.2 and npm with frozen lockfiles
- Codex, the official Chrome integration, and the official Gmail connector
- macOS Keychain or Windows Credential Locker for full support

Linux supports the tracker, Gmail, dashboards, Chrome where available, and supported secure keyring backends, but not full Computer Use parity.

Install uv from the [official installation guide](https://docs.astral.sh/uv/getting-started/installation/) if `uv --version` is not available.

## Install and diagnose

Install the complete plugin rather than copying only `SKILL.md`; the plugin also provides its Gmail app configuration, supporting scripts, references, and default configuration.

Clone the public repository on the target machine:

```bash
git clone https://github.com/LuizFelipeBarbosa/job-application-skill.git
cd job-application-skill
```

Register the repository marketplace and install the plugin with the Codex CLI:

```bash
codex plugin marketplace add .
codex plugin add job-application-suite@personal
```

The `personal` marketplace name comes from `.agents/plugins/marketplace.json`. To install through the desktop app instead, open the cloned repository in Codex, restart the app, open **Plugins**, select the **Personal** marketplace, and install **Job Application Suite**. Complete the Gmail authorization when prompted and make sure the official Chrome and Computer Use plugins are enabled.

Repo-scoped `.agents` and `.claude` links point to the plugin's single canonical skill copy. Restart Codex after a CLI installation and use a new task so the installed skill is available as `job-application-suite:apply-to-jobs`.

Create the isolated, lockfile-backed Python runtime without recording credentials. Bootstrap runs `uv sync --locked` against the skill's `pyproject.toml` and `uv.lock`, while keeping the environment at `.runtime/venv`:

```bash
python3 plugins/job-application-suite/skills/apply-to-jobs/scripts/bootstrap.py
```

Run the read-only local diagnostic:

```bash
.runtime/venv/bin/python \
  plugins/job-application-suite/skills/apply-to-jobs/scripts/doctor.py \
  --workspace . --format human
```

On Windows, use `.runtime\venv\Scripts\python.exe`. Doctor exits `0` for pass/warnings, `1` for a missing required capability, and `2` for invalid configuration. JSON output is available with `--format json`.

Live Gmail, Chrome, upload, and Computer Use probes run only when explicitly requested. They use a profile check and the local synthetic fixture; they do not read ordinary mail, job-site data, or credentials.

## Configure and run

Workspace files in `config/` override the plugin defaults only after schema validation. Handshake is enabled by default. Chrome onboarding should grant Handshake and then approve each verified employer ATS domain once; never choose **Allow for all sites**.

Prepare truthful candidate data under ignored `private/` storage:

```bash
mkdir -p private/documents
cp plugins/job-application-suite/skills/apply-to-jobs/assets/candidate-profile.md \
  private/candidate-profile.md
```

Then ask for a positive bounded target, for example:

```text
Apply to 5 matching new-grad software engineering jobs. Review each before submission.
```

That request authorizes ordinary accounts required solely for this bounded run. The run brief discloses the authorization before browser data entry. Paid services, public profiles, marketing, unusual terms, and changes to existing-account security still require confirmation.

Gmail beta access is provider-neutral in design but ships only the Gmail adapter. It permits profile, narrow search, and selected-message read operations. Sending, drafting, forwarding, archiving, deleting, and labeling are prohibited.

## Local dashboards

The analytics dashboard is available normally:

```bash
cd dashboard
pnpm install --frozen-lockfile
pnpm dev
```

Account Vault is disabled in ordinary launches. Enable it for one process with `pnpm dev:vault` or, after a build, `pnpm start:vault`, then open the printed fragment-token URL. The token is fresh for each launch, removed from the address bar, kept in tab session storage, and sent only as a bearer header. Passwords never enter HTTP responses.

The diagnostic fixture is at `http://127.0.0.1:3000/diagnostics/browser` and must be used only with the bundled synthetic upload.

The vendored `dashboard-sites/` companion permanently excludes credential operations and private fields. See its README for user-owned D1 provisioning and self-deployment; never use another installation's Sites project.

## Security and beta status

Read [SECURITY.md](SECURITY.md), [PRIVACY.md](PRIVACY.md), [docs/PLATFORM_SUPPORT.md](docs/PLATFORM_SUPPORT.md), and [docs/BETA_LIMITATIONS.md](docs/BETA_LIMITATIONS.md). `0.1.0-beta.1` is publishable only after automated checks and the macOS and Windows acceptance records in [docs/BETA_ACCEPTANCE.md](docs/BETA_ACCEPTANCE.md) are complete.
