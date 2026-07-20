import { chmod, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const [trackerArgument, outputArgument, outcomesArgument] = process.argv.slice(2);
if (!trackerArgument || !outputArgument) {
  throw new Error(
    "Usage: node scripts/export-sanitized-applications.mjs TRACKER_PATH OUTPUT_PATH [OUTCOMES_PATH]",
  );
}

const trackerPath = path.resolve(trackerArgument);
const outputPath = path.resolve(outputArgument);
const tracker = JSON.parse(await readFile(trackerPath, "utf8"));
if (!Array.isArray(tracker.runs)) throw new Error("Tracker runs are missing.");

let outcomes = { applications: {} };
if (outcomesArgument) {
  try {
    const parsed = JSON.parse(await readFile(path.resolve(outcomesArgument), "utf8"));
    if (parsed && typeof parsed.applications === "object" && !Array.isArray(parsed.applications)) {
      outcomes = parsed;
    }
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}

function safeText(value, maximumLength = 5_000) {
  return typeof value === "string" ? value.trim().slice(0, maximumLength) : "";
}

function safeHttpsUrl(value) {
  if (typeof value !== "string") return "";
  try {
    const url = new URL(value);
    if (url.protocol !== "https:" || url.username || url.password) return "";
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return "";
  }
}

function deriveJobType(title) {
  const normalized = safeText(title).toLowerCase();
  if (/\b(intern|internship|co-?op)\b/.test(normalized)) return "Internship / co-op";
  if (/\b(apprentice|apprenticeship|fellow|fellowship|residen(?:t|cy))\b/.test(normalized)) {
    return "Apprenticeship / fellowship";
  }
  if (/\b(contract|contractor|temporary|temp)\b/.test(normalized)) return "Contract / temporary";
  if (/\bpart[- ]?time\b/.test(normalized)) return "Part-time";
  return "Full-time / unspecified";
}

function safeTimestamp(value) {
  if (typeof value !== "string") return "";
  return Number.isNaN(Date.parse(value)) ? "" : value;
}

function sanitizeStatusHistory(transitions) {
  if (!Array.isArray(transitions)) return [];
  return transitions.flatMap((transition) => {
    if (!transition || typeof transition !== "object") return [];
    const at = safeTimestamp(transition.at);
    const to = safeText(transition.to, 100);
    if (!at || !to) return [];
    return [{
      at,
      from: transition.from === null ? null : safeText(transition.from, 100) || null,
      to,
      reasonCode: safeText(transition.reason_code, 200),
    }];
  });
}

function sanitizeStageHistory(history, appliedAt) {
  const entries = Array.isArray(history)
    ? history.flatMap((entry) => {
        if (!entry || typeof entry !== "object") return [];
        const at = safeTimestamp(entry.at);
        const stage = safeText(entry.stage, 100);
        return at && stage ? [{ at, stage }] : [];
      })
    : [];
  if (appliedAt && !entries.some((entry) => entry.stage === "applied")) {
    entries.unshift({ stage: "applied", at: appliedAt });
  }
  return entries;
}

const applications = tracker.runs.flatMap((run) => {
  if (!run || typeof run !== "object" || !Array.isArray(run.applications)) return [];
  return run.applications.map((application) => {
    const status = ["submitted", "blocked", "skipped"].includes(application.status)
      ? application.status
      : "in_progress";
    const history = sanitizeStatusHistory(application.transitions);
    const submittedAt = status === "submitted"
      ? history.find((entry) => entry.to === "submitted")?.at || safeTimestamp(application.recorded_at)
      : "";
    const outcome = status === "submitted" && outcomes.applications
      ? outcomes.applications[String(application.id ?? "")]
      : null;

    return {
      id: safeText(String(application.id ?? ""), 500),
      runId: safeText(String(run.id ?? ""), 500),
      runStatus: safeText(run.status, 100),
      runTarget: Number.isInteger(run.target) && run.target >= 0 ? run.target : 0,
      runCreatedAt: safeTimestamp(run.created_at),
      runCompletedAt: safeTimestamp(run.completed_at),
      company: safeText(application.company, 500) || "Unknown company",
      title: safeText(application.title, 500) || "Untitled role",
      jobType: deriveJobType(application.title),
      jobId: safeText(application.job_id, 500),
      location: safeText(application.location, 500) || "Not specified",
      site: safeText(application.site, 300) || "Unknown source",
      url: safeHttpsUrl(application.url),
      canonicalUrl: safeHttpsUrl(application.canonical_url),
      status,
      reasonCode: safeText(application.reason_code, 200),
      statusHistory: history,
      createdAt: safeTimestamp(application.created_at),
      recordedAt: safeTimestamp(application.recorded_at),
      updatedAt: safeTimestamp(application.updated_at),
      submittedAt,
      generatedAnswerCount: Number.isInteger(application.generated_answer_count)
        ? Math.max(application.generated_answer_count, 0)
        : 0,
      inferredAnswerCount: Number.isInteger(application.inferred_answer_count)
        ? Math.max(application.inferred_answer_count, 0)
        : 0,
      careerStage: status === "submitted" ? safeText(outcome?.stage, 100) || "applied" : "",
      careerStageUpdatedAt: status === "submitted"
        ? safeTimestamp(outcome?.stage_updated_at) || submittedAt
        : "",
      nextActionDueAt: status === "submitted" ? safeTimestamp(outcome?.next_action_due_at) : "",
      stageHistory: status === "submitted"
        ? sanitizeStageHistory(outcome?.stage_history, submittedAt)
        : [],
    };
  });
});

const APPLICATION_FIELDS = new Set([
  "id", "runId", "runStatus", "runTarget", "runCreatedAt", "runCompletedAt", "company",
  "title", "jobType", "jobId", "location", "site", "url", "canonicalUrl", "status",
  "reasonCode", "statusHistory", "createdAt", "recordedAt", "updatedAt", "submittedAt",
  "generatedAnswerCount", "inferredAnswerCount", "careerStage", "careerStageUpdatedAt",
  "nextActionDueAt", "stageHistory",
]);
const STATUS_HISTORY_FIELDS = new Set(["at", "from", "to", "reasonCode"]);
const STAGE_HISTORY_FIELDS = new Set(["at", "stage"]);

function rejectUnknownFields(record, allowedFields, context) {
  const unknownFields = Object.keys(record).filter((field) => !allowedFields.has(field));
  if (unknownFields.length) {
    throw new Error(`${context} contains non-allowlisted fields: ${unknownFields.join(", ")}`);
  }
}

for (const application of applications) {
  rejectUnknownFields(application, APPLICATION_FIELDS, `Application ${application.id}`);
  for (const entry of application.statusHistory) {
    rejectUnknownFields(entry, STATUS_HISTORY_FIELDS, `Status history for ${application.id}`);
  }
  for (const entry of application.stageHistory) {
    rejectUnknownFields(entry, STAGE_HISTORY_FIELDS, `Stage history for ${application.id}`);
  }
}

const serializedApplications = JSON.stringify(applications);
if (/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i.test(serializedApplications)) {
  throw new Error("Sanitized export contains an email address.");
}
if (/\b(password|passcode|secret|token|api[ _-]?key)\s*[:=]/i.test(serializedApplications)) {
  throw new Error("Sanitized export contains a credential-like value.");
}

if (!applications.length || applications.some((application) => !application.id)) {
  throw new Error("The tracker did not contain valid application IDs.");
}
if (new Set(applications.map((application) => application.id)).size !== applications.length) {
  throw new Error("The tracker contains duplicate application IDs.");
}

await writeFile(outputPath, `${JSON.stringify({ applications })}\n`, { mode: 0o600 });
await chmod(outputPath, 0o600);
process.stdout.write(`${applications.length} sanitized applications exported\n`);
