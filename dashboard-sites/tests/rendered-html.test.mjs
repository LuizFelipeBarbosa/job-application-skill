import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { access, mkdtemp, readFile, readdir, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";
import { promisify } from "node:util";

const projectRoot = new URL("../", import.meta.url);
const runFile = promisify(execFile);

test("defines the hosted-safe command center and social metadata", async () => {
  const [component, layout] = await Promise.all([
    readFile(new URL("../app/hosted-dashboard.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
  ]);
  assert.match(layout, /title: "Job Search Command Center"/);
  assert.match(layout, /\/og\.png/);
  assert.match(component, /The application/);
  assert.match(component, /command center\./);
  assert.match(component, /Private database connected\./);
  assert.match(component, /HOSTED SAFE MODE/);
  assert.doesNotMatch(`${component}\n${layout}`, /codex-preview|react-loading-skeleton|type="password"/i);
});

test("keeps tracker previews local, mobile controls usable, and credential access disabled", async () => {
  const [component, route, exporter, layout, page, styles, packageJson] = await Promise.all([
    readFile(new URL("../app/hosted-dashboard.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/api/applications/route.ts", import.meta.url), "utf8"),
    readFile(new URL("../scripts/export-sanitized-applications.mjs", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../package.json", import.meta.url), "utf8"),
  ]);

  assert.match(component, /file\.text\(\)/);
  assert.match(component, /fetch\("\/api\/applications"/);
  assert.match(component, /aria-controls="application-filters"/);
  assert.match(component, /data-label="Application"/);
  assert.match(component, /data-label="Submitted \/ recorded"/);
  assert.match(component, /<colgroup>/);
  assert.match(component, /className="application-primary"/);
  assert.match(component, /className="status-stack"/);
  assert.match(component, /Job type breakdown/);
  assert.match(component, /Why this role was blocked/);
  assert.match(component, /Status timeline/);
  assert.match(component, /filtered\.map/);
  assert.doesNotMatch(component, /filtered\.slice\(0,\s*100\)/);
  assert.match(component, /cannot reach the operating-system credential vault/);
  assert.doesNotMatch(component, /copy-password|clear-clipboard|password_manager/);
  assert.match(route, /export async function GET/);
  assert.doesNotMatch(route, /export async function POST|IMPORT_SECRET|authorization/i);
  assert.match(route, /getChatGPTUser/);
  assert.match(page, /requireChatGPTUser/);
  assert.match(route, /status_history_json AS statusHistoryJson/);
  assert.match(route, /job_type AS jobType/);
  assert.doesNotMatch(`${component}\n${route}\n${exporter}`, /trackerNote|outcomeNotes|runObjective|evidence_refs|document_signatures|profile_signature|browser_session|worker_metadata/);
  assert.match(layout, /metadataBase/);
  assert.match(styles, /@media \(max-width: 390px\)/);
  assert.match(styles, /\.filter-toggle/);
  assert.match(styles, /td::before/);
  assert.match(styles, /table-layout: fixed/);
  assert.match(styles, /vertical-align: top/);
  assert.doesNotMatch(styles, /td:first-child\s*\{[^}]*display:\s*grid/);
  assert.match(styles, /position: sticky/);
  assert.doesNotMatch(packageJson, /react-loading-skeleton/);
  const migrationNames = (await readdir(new URL("../drizzle", import.meta.url)))
    .filter((name) => name.endsWith(".sql"));
  const migrations = (
    await Promise.all(
      migrationNames.map((name) => readFile(new URL(`../drizzle/${name}`, import.meta.url), "utf8")),
    )
  ).join("\n");
  assert.doesNotMatch(migrations, /run_objective|tracker_note|next_action\s|outcome_notes|candidate|email|password|passcode|token|browser_session|signature|evidence/);
  await assert.rejects(access(new URL("app/_sites-preview", projectRoot)));
});

test("exports only allowlisted records and rejects unsafe D1 imports", async () => {
  const temporaryDirectory = await mkdtemp(path.join(tmpdir(), "job-dashboard-export-"));
  const trackerPath = path.join(temporaryDirectory, "tracker.json");
  const outputPath = path.join(temporaryDirectory, "applications.json");
  const tracker = {
    schema_version: 1,
    runs: [{
      id: "run-1",
      objective: "Test run",
      status: "complete",
      target: 2,
      created_at: "2026-07-01T00:00:00Z",
      completed_at: "2026-07-02T00:00:00Z",
      applications: [{
        id: "app-1",
        company: "Example",
        title: "Software Engineering Intern",
        location: "Remote",
        site: "Example ATS",
        url: "https://example.com/job",
        canonical_url: "https://example.com/job/1",
        status: "blocked",
        reason_code: "secure_password_entry",
        note: "Password: super-secret for candidate@example.com",
        next_action: "Enter the credential locally",
        created_at: "2026-07-01T00:00:00Z",
        recorded_at: "2026-07-01T00:01:00Z",
        updated_at: "2026-07-01T00:02:00Z",
        generated_answer_count: 3,
        inferred_answer_count: 4,
        browser_session: { secret: "never-export" },
        confirmation: { value: "never-export" },
        transitions: [{
          at: "2026-07-01T00:02:00Z",
          from: "in_progress",
          to: "blocked",
          reason_code: "secure_password_entry",
          note: "Password: super-secret for candidate@example.com",
          next_action: "Enter the credential locally",
          worker: { secret: "never-export" },
        }],
      }],
    }],
  };

  try {
    await writeFile(trackerPath, JSON.stringify(tracker));
    await runFile(process.execPath, [
      new URL("../scripts/export-sanitized-applications.mjs", import.meta.url).pathname,
      trackerPath,
      outputPath,
    ]);
    const payload = JSON.parse(await readFile(outputPath, "utf8"));
    assert.equal(payload.applications.length, 1);
    const application = payload.applications[0];
    assert.equal(application.jobType, "Internship / co-op");
    assert.equal(application.reasonCode, "secure_password_entry");
    assert.equal(application.statusHistory.length, 1);
    assert.doesNotMatch(JSON.stringify(payload), /super-secret|candidate@example\.com|never-export/);
    assert.equal("trackerNote" in application, false);
    assert.equal("outcomeNotes" in application, false);
    assert.equal("runObjective" in application, false);
    assert.equal("browser_session" in application, false);
    assert.equal("confirmation" in application, false);

    const importPath = path.join(temporaryDirectory, "import.sql");
    await runFile(process.execPath, [
      new URL("../scripts/prepare-d1-import.mjs", import.meta.url).pathname,
      outputPath,
      importPath,
    ]);
    const sql = await readFile(importPath, "utf8");
    assert.doesNotMatch(sql, /super-secret|candidate@example\.com|tracker_note|outcome_notes/);

    payload.applications[0].privateNotes = "must not reach D1";
    await writeFile(outputPath, JSON.stringify(payload));
    await assert.rejects(
      runFile(process.execPath, [
        new URL("../scripts/prepare-d1-import.mjs", import.meta.url).pathname,
        outputPath,
        importPath,
      ]),
      /non-allowlisted fields/,
    );
  } finally {
    await rm(temporaryDirectory, { recursive: true, force: true });
  }
});
