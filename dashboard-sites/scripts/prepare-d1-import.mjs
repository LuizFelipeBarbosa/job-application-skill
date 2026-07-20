import { chmod, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";

const [inputArgument, outputArgument] = process.argv.slice(2);
if (!inputArgument || !outputArgument) {
  throw new Error("Usage: npm run db:import:prepare -- SANITIZED_JSON OUTPUT_SQL");
}

const applicationFields = [
  "id", "runId", "runStatus", "runTarget", "runCreatedAt", "runCompletedAt", "company",
  "title", "jobType", "jobId", "location", "site", "url", "canonicalUrl", "status",
  "reasonCode", "statusHistory", "createdAt", "recordedAt", "updatedAt", "submittedAt",
  "generatedAnswerCount", "inferredAnswerCount", "careerStage", "careerStageUpdatedAt",
  "nextActionDueAt", "stageHistory",
];
const applicationFieldSet = new Set(applicationFields);
const historyFields = new Set(["at", "from", "to", "reasonCode"]);
const stageFields = new Set(["at", "stage"]);

function rejectUnknownFields(record, allowedFields, context) {
  if (!record || typeof record !== "object" || Array.isArray(record)) {
    throw new Error(`${context} must be an object.`);
  }
  const unknownFields = Object.keys(record).filter((field) => !allowedFields.has(field));
  if (unknownFields.length) {
    throw new Error(`${context} contains non-allowlisted fields: ${unknownFields.join(", ")}`);
  }
  const missingFields = [...allowedFields].filter(
    (field) => !Object.prototype.hasOwnProperty.call(record, field),
  );
  if (missingFields.length) {
    throw new Error(`${context} is missing allowlisted fields: ${missingFields.join(", ")}`);
  }
}

function sqlString(value) {
  return `'${String(value ?? "").replaceAll("'", "''")}'`;
}

const inputPath = path.resolve(inputArgument);
const outputPath = path.resolve(outputArgument);
const payload = JSON.parse(await readFile(inputPath, "utf8"));
rejectUnknownFields(payload, new Set(["applications"]), "Export payload");
if (!Array.isArray(payload.applications) || !payload.applications.length) {
  throw new Error("Export payload must contain at least one application.");
}

for (const [index, application] of payload.applications.entries()) {
  rejectUnknownFields(application, applicationFieldSet, `Application ${index}`);
  if (!application.id || typeof application.id !== "string") {
    throw new Error(`Application ${index} has no valid ID.`);
  }
  if (!Array.isArray(application.statusHistory) || !Array.isArray(application.stageHistory)) {
    throw new Error(`Application ${application.id} has invalid history fields.`);
  }
  application.statusHistory.forEach((entry) =>
    rejectUnknownFields(entry, historyFields, `Status history for ${application.id}`),
  );
  application.stageHistory.forEach((entry) =>
    rejectUnknownFields(entry, stageFields, `Stage history for ${application.id}`),
  );
}

if (new Set(payload.applications.map((application) => application.id)).size !== payload.applications.length) {
  throw new Error("Import contains duplicate application IDs.");
}

const serialized = JSON.stringify(payload);
if (/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(serialized)) {
  throw new Error("Import contains candidate contact data.");
}
if (/\b(password|passcode|secret|token|api[ _-]?key)\s*[:=]/i.test(serialized)) {
  throw new Error("Import contains credential-like data.");
}

const databaseColumns = [
  "id", "run_id", "run_status", "run_target", "run_created_at", "run_completed_at",
  "company", "title", "job_type", "job_id", "location", "site", "url", "canonical_url",
  "automation_status", "reason_code", "status_history_json", "created_at", "recorded_at",
  "updated_at", "submitted_at", "generated_answer_count", "inferred_answer_count",
  "career_stage", "career_stage_updated_at", "next_action_due_at", "stage_history_json",
  "import_id", "imported_at",
];
const importedAt = new Date().toISOString();
const importId = randomUUID();
const rows = payload.applications.map((application) => [
  application.id, application.runId, application.runStatus, application.runTarget,
  application.runCreatedAt, application.runCompletedAt, application.company, application.title,
  application.jobType, application.jobId, application.location, application.site, application.url,
  application.canonicalUrl, application.status, application.reasonCode,
  JSON.stringify(application.statusHistory), application.createdAt, application.recordedAt,
  application.updatedAt, application.submittedAt, application.generatedAnswerCount,
  application.inferredAnswerCount, application.careerStage, application.careerStageUpdatedAt,
  application.nextActionDueAt, JSON.stringify(application.stageHistory), importId, importedAt,
]);
const statements = rows.map((row) =>
  `INSERT INTO applications (${databaseColumns.join(", ")}) VALUES (${row.map(sqlString).join(", ")});`,
);
const sql = ["DELETE FROM applications;", ...statements, ""].join("\n");
await writeFile(outputPath, sql, { mode: 0o600 });
await chmod(outputPath, 0o600);
process.stdout.write(`${rows.length} validated applications prepared for D1\n`);
