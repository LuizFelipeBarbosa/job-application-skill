"use client";

import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

type AutomationStatus = "submitted" | "blocked" | "skipped" | "ready_to_submit" | "in_progress";

type StatusHistoryEntry = {
  at: string;
  from: string | null;
  to: string;
  reasonCode: string;
};

type StageHistoryEntry = {
  at: string;
  stage: string;
};

type Application = {
  id: string;
  runId: string;
  runStatus: string;
  runTarget: number;
  runCreatedAt: string;
  runCompletedAt: string;
  company: string;
  title: string;
  jobType: string;
  jobId: string;
  location: string;
  site: string;
  url: string;
  canonicalUrl: string;
  status: AutomationStatus;
  reasonCode: string;
  statusHistory: StatusHistoryEntry[];
  createdAt: string;
  recordedAt: string;
  updatedAt: string;
  submittedAt: string;
  generatedAnswerCount: number;
  inferredAnswerCount: number;
  careerStage: string;
  careerStageUpdatedAt: string;
  nextActionDueAt: string;
  stageHistory: StageHistoryEntry[];
  importedAt?: string;
};

const sampleApplications: Application[] = [
  {
    id: "sample-1", runId: "Sample run", runStatus: "complete", runTarget: 4,
    runCreatedAt: "2026-07-14T17:00:00Z", runCompletedAt: "2026-07-18T20:00:00Z", company: "Northstar Labs",
    title: "Data Analyst", jobType: "Full-time / unspecified", jobId: "", location: "San Francisco, CA", site: "Greenhouse",
    url: "https://example.com", canonicalUrl: "", status: "submitted", reasonCode: "",
    statusHistory: [{ at: "2026-07-14T17:00:00Z", from: null, to: "submitted", reasonCode: "" }],
    createdAt: "2026-07-14T17:00:00Z", recordedAt: "2026-07-14T17:00:00Z", updatedAt: "2026-07-14T17:00:00Z",
    submittedAt: "2026-07-14T17:00:00Z", generatedAnswerCount: 0, inferredAnswerCount: 0, careerStage: "applied",
    careerStageUpdatedAt: "2026-07-14T17:00:00Z", nextActionDueAt: "", stageHistory: [{ stage: "applied", at: "2026-07-14T17:00:00Z" }],
  },
  {
    id: "sample-2", runId: "Sample run", runStatus: "complete", runTarget: 4,
    runCreatedAt: "2026-07-14T17:00:00Z", runCompletedAt: "2026-07-18T20:00:00Z", company: "Cedar Systems",
    title: "Product Analyst Intern", jobType: "Internship / co-op", jobId: "", location: "Remote", site: "Ashby",
    url: "https://example.com", canonicalUrl: "", status: "submitted", reasonCode: "",
    statusHistory: [{ at: "2026-07-15T18:00:00Z", from: null, to: "submitted", reasonCode: "" }],
    createdAt: "2026-07-15T18:00:00Z", recordedAt: "2026-07-15T18:00:00Z", updatedAt: "2026-07-15T18:00:00Z",
    submittedAt: "2026-07-15T18:00:00Z", generatedAnswerCount: 0, inferredAnswerCount: 0, careerStage: "applied",
    careerStageUpdatedAt: "2026-07-15T18:00:00Z", nextActionDueAt: "", stageHistory: [{ stage: "applied", at: "2026-07-15T18:00:00Z" }],
  },
  {
    id: "sample-3", runId: "Sample run", runStatus: "complete", runTarget: 4,
    runCreatedAt: "2026-07-14T17:00:00Z", runCompletedAt: "2026-07-18T20:00:00Z", company: "Harbor Works",
    title: "Research Associate", jobType: "Full-time / unspecified", jobId: "", location: "Seattle, WA", site: "Lever",
    url: "https://example.com", canonicalUrl: "", status: "blocked", reasonCode: "missing_required_information",
    statusHistory: [{ at: "2026-07-16T19:00:00Z", from: "in_progress", to: "blocked", reasonCode: "missing_required_information" }],
    createdAt: "2026-07-16T19:00:00Z", recordedAt: "2026-07-16T19:00:00Z", updatedAt: "2026-07-16T19:00:00Z",
    submittedAt: "", generatedAnswerCount: 0, inferredAnswerCount: 0, careerStage: "", careerStageUpdatedAt: "",
    nextActionDueAt: "", stageHistory: [],
  },
];

function text(value: unknown, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function deriveJobType(title: string) {
  const normalized = title.toLowerCase();
  if (/\b(intern|internship|co-?op)\b/.test(normalized)) return "Internship / co-op";
  if (/\b(apprentice|apprenticeship|fellow|fellowship|residen(?:t|cy))\b/.test(normalized)) return "Apprenticeship / fellowship";
  if (/\b(contract|contractor|temporary|temp)\b/.test(normalized)) return "Contract / temporary";
  if (/\bpart[- ]?time\b/.test(normalized)) return "Part-time";
  return "Full-time / unspecified";
}

function normalizeTracker(raw: unknown): Application[] {
  if (!raw || typeof raw !== "object") throw new Error("This is not a tracker file.");
  const runs = (raw as { runs?: unknown }).runs;
  if (!Array.isArray(runs)) throw new Error("The tracker does not contain any runs.");

  const applications: Application[] = [];
  for (const run of runs) {
    if (!run || typeof run !== "object") continue;
    const runRecord = run as Record<string, unknown>;
    const runId = text(runRecord.id, "Unknown run");
    if (!Array.isArray(runRecord.applications)) continue;
    for (const item of runRecord.applications) {
      if (!item || typeof item !== "object") continue;
      const source = item as Record<string, unknown>;
      const rawStatus = text(source.status, "in_progress");
      const status: AutomationStatus = ["submitted", "blocked", "skipped", "ready_to_submit"].includes(rawStatus)
        ? rawStatus as AutomationStatus
        : "in_progress";
      const transitions: StatusHistoryEntry[] = Array.isArray(source.transitions)
        ? source.transitions.flatMap((entry) => {
            if (!entry || typeof entry !== "object") return [];
            const transition = entry as Record<string, unknown>;
            const at = text(transition.at);
            const to = text(transition.to);
            return at && to ? [{
              at,
              from: transition.from === null ? null : text(transition.from) || null,
              to,
              reasonCode: text(transition.reason_code),
            }] : [];
          })
        : [];
      const recordedAt = text(source.recorded_at);
      const submittedAt = status === "submitted"
        ? transitions.find((entry) => entry.to === "submitted")?.at || recordedAt
        : "";
      const title = text(source.title, "Untitled role");
      const rawUrl = text(source.url);
      const canonicalUrl = text(source.canonical_url);

      applications.push({
        id: text(source.id, `${runId}-${applications.length}`),
        runId,
        runStatus: text(runRecord.status),
        runTarget: typeof runRecord.target === "number" ? runRecord.target : 0,
        runCreatedAt: text(runRecord.created_at),
        runCompletedAt: text(runRecord.completed_at),
        company: text(source.company, "Unknown company"),
        title,
        jobType: deriveJobType(title),
        jobId: text(source.job_id),
        location: text(source.location, "Not specified"),
        site: text(source.site, "Unknown source"),
        url: rawUrl.startsWith("https://") ? rawUrl : "",
        canonicalUrl: canonicalUrl.startsWith("https://") ? canonicalUrl : "",
        status,
        reasonCode: text(source.reason_code),
        statusHistory: transitions,
        createdAt: text(source.created_at),
        recordedAt,
        updatedAt: text(source.updated_at),
        submittedAt,
        generatedAnswerCount: typeof source.generated_answer_count === "number" ? source.generated_answer_count : 0,
        inferredAnswerCount: typeof source.inferred_answer_count === "number" ? source.inferred_answer_count : 0,
        careerStage: status === "submitted" ? "applied" : "",
        careerStageUpdatedAt: submittedAt,
        nextActionDueAt: "",
        stageHistory: status === "submitted" && submittedAt ? [{ stage: "applied", at: submittedAt }] : [],
      });
    }
  }
  if (!applications.length) throw new Error("No application records were found.");
  return applications;
}

function countBy(items: Application[], key: "status" | "site" | "location" | "jobType") {
  const counts = new Map<string, number>();
  for (const item of items) counts.set(item[key], (counts.get(item[key]) ?? 0) + 1);
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}

function humanize(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value: string, withTime = false) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return "—";
  return new Intl.DateTimeFormat(undefined, withTime
    ? { dateStyle: "medium", timeStyle: "short" }
    : { dateStyle: "medium" }).format(date);
}

function BarList({ rows, color = "blue" }: { rows: Array<[string, number]>; color?: "blue" | "orange" | "olive" }) {
  const maximum = Math.max(...rows.map(([, value]) => value), 1);
  return (
    <div className="bar-list" role="img" aria-label={rows.map(([label, value]) => `${label}: ${value}`).join(", ")}>
      {rows.map(([label, value]) => (
        <div className="bar-row" key={label}>
          <span title={label}>{humanize(label)}</span>
          <div className="bar-track"><i className={color} style={{ width: `${Math.max((value / maximum) * 100, 2)}%` }} /></div>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function DetailField({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="detail-field"><dt>{label}</dt><dd>{children || "—"}</dd></div>;
}

function ApplicationDetails({ application, onClose }: { application: Application; onClose: () => void }) {
  const reasonLabel = application.status === "blocked"
    ? "Why this role was blocked"
    : application.status === "skipped"
      ? "Why this role was skipped"
      : "Tracker note";

  return (
    <div className="drawer-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="detail-drawer" role="dialog" aria-modal="true" aria-labelledby="application-detail-title">
        <header className="drawer-head">
          <div><p className="eyebrow">COMPLETE SAFE RECORD</p><h2 id="application-detail-title">{application.company}</h2><p>{application.title}</p></div>
          <button type="button" onClick={onClose} aria-label="Close application details">Close</button>
        </header>

        <div className="detail-status">
          <b className={`status ${application.status}`}>{humanize(application.status)}</b>
          {application.careerStage && <span>Career stage · {humanize(application.careerStage)}</span>}
          <span>{application.jobType} · inferred from title</span>
        </div>

        {application.reasonCode && (
          <section className="reason-card">
            <p className="eyebrow">{reasonLabel}</p>
            <code>{humanize(application.reasonCode)}</code>
          </section>
        )}

        <section className="detail-section">
          <h3>Role & source</h3>
          <dl className="detail-grid">
            <DetailField label="Company">{application.company}</DetailField>
            <DetailField label="Role">{application.title}</DetailField>
            <DetailField label="Job type">{application.jobType} <small>inferred from title</small></DetailField>
            <DetailField label="Location">{application.location}</DetailField>
            <DetailField label="Source">{application.url ? <a href={application.url} target="_blank" rel="noreferrer">Open on {application.site}</a> : application.site}</DetailField>
            <DetailField label="Job ID">{application.jobId || "Not supplied"}</DetailField>
            {application.canonicalUrl && application.canonicalUrl !== application.url && <DetailField label="Canonical listing"><a href={application.canonicalUrl} target="_blank" rel="noreferrer">Open canonical URL</a></DetailField>}
          </dl>
        </section>

        <section className="detail-section">
          <h3>Application lifecycle</h3>
          <dl className="detail-grid">
            <DetailField label="Automation status">{humanize(application.status)}</DetailField>
            <DetailField label="Career stage">{application.careerStage ? humanize(application.careerStage) : "Not in employer pipeline"}</DetailField>
            <DetailField label="Created">{formatDate(application.createdAt, true)}</DetailField>
            <DetailField label="Recorded">{formatDate(application.recordedAt, true)}</DetailField>
            <DetailField label="Last updated">{formatDate(application.updatedAt, true)}</DetailField>
            <DetailField label="Submitted">{formatDate(application.submittedAt, true)}</DetailField>
            <DetailField label="Stage updated">{formatDate(application.careerStageUpdatedAt, true)}</DetailField>
            <DetailField label="Follow-up due">{formatDate(application.nextActionDueAt, true)}</DetailField>
            <DetailField label="Generated answers">{application.generatedAnswerCount}</DetailField>
            <DetailField label="Profile-inferred answers">{application.inferredAnswerCount}</DetailField>
          </dl>
        </section>

        <section className="detail-section">
          <h3>Run context</h3>
          <dl className="detail-grid">
            <DetailField label="Run ID"><code>{application.runId}</code></DetailField>
            <DetailField label="Run status">{humanize(application.runStatus)}</DetailField>
            <DetailField label="Run target">{application.runTarget}</DetailField>
            <DetailField label="Run started">{formatDate(application.runCreatedAt, true)}</DetailField>
            <DetailField label="Run completed">{formatDate(application.runCompletedAt, true)}</DetailField>
          </dl>
        </section>

        <section className="detail-section">
          <h3>Status timeline</h3>
          {application.statusHistory.length ? (
            <ol className="timeline">
              {application.statusHistory.map((entry, index) => (
                <li key={`${entry.at}-${entry.to}-${index}`}>
                  <time>{formatDate(entry.at, true)}</time>
                  <strong>{entry.from ? `${humanize(entry.from)} → ` : ""}{humanize(entry.to)}</strong>
                  {entry.reasonCode && <code>{humanize(entry.reasonCode)}</code>}
                </li>
              ))}
            </ol>
          ) : <p className="empty-detail">No tracker transitions were recorded.</p>}
        </section>

        {application.stageHistory.length > 0 && (
          <section className="detail-section">
            <h3>Employer pipeline history</h3>
            <ol className="timeline compact">
              {application.stageHistory.map((entry, index) => <li key={`${entry.at}-${entry.stage}-${index}`}><time>{formatDate(entry.at, true)}</time><strong>{humanize(entry.stage)}</strong></li>)}
            </ol>
          </section>
        )}
      </section>
    </div>
  );
}

export function HostedDashboard() {
  const [applications, setApplications] = useState(sampleApplications);
  const [sourceLabel, setSourceLabel] = useState("Sample records");
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"overview" | "applications" | "vault">("overview");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [source, setSource] = useState("all");
  const [location, setLocation] = useState("all");
  const [jobType, setJobType] = useState("all");
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [selectedApplication, setSelectedApplication] = useState<Application | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/applications", { cache: "no-store" })
      .then((response) => response.ok ? response.json() : Promise.reject(new Error("unavailable")))
      .then((payload: { applications?: Application[]; snapshotAt?: string }) => {
        if (!active || !Array.isArray(payload.applications) || !payload.applications.length) return;
        setApplications(payload.applications);
        const snapshot = payload.snapshotAt ? ` · snapshot ${formatDate(payload.snapshotAt, true)}` : "";
        setSourceLabel(`Private database · ${payload.applications.length} records${snapshot}`);
      })
      .catch(() => {
        if (active) setError("The private application store is temporarily unavailable; sample records are shown.");
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!selectedApplication) return;
    const closeOnEscape = (event: KeyboardEvent) => event.key === "Escape" && setSelectedApplication(null);
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [selectedApplication]);

  const sources = useMemo(() => [...new Set(applications.map((item) => item.site))].sort(), [applications]);
  const locations = useMemo(() => [...new Set(applications.map((item) => item.location))].sort(), [applications]);
  const jobTypes = useMemo(() => [...new Set(applications.map((item) => item.jobType))].sort(), [applications]);
  const filtered = useMemo(() => applications.filter((item) => {
    const haystack = `${item.company} ${item.title} ${item.location} ${item.site} ${item.jobType} ${item.reasonCode}`.toLowerCase();
    const matchesText = haystack.includes(query.toLowerCase());
    return matchesText
      && (status === "all" || item.status === status)
      && (source === "all" || item.site === source)
      && (location === "all" || item.location === location)
      && (jobType === "all" || item.jobType === jobType);
  }), [applications, jobType, location, query, source, status]);

  const submitted = filtered.filter((item) => item.status === "submitted").length;
  const finalAttempts = filtered.filter((item) => ["submitted", "blocked", "skipped"].includes(item.status)).length;
  const yieldRate = finalAttempts ? (submitted / finalAttempts) * 100 : 0;
  const sourceRows = countBy(filtered.filter((item) => item.status === "submitted"), "site").slice(0, 6);
  const locationRows = countBy(filtered, "location").slice(0, 6);
  const outcomeRows = countBy(filtered, "status");
  const jobTypeRows = countBy(filtered, "jobType");

  function resetFilters() {
    setQuery("");
    setStatus("all");
    setSource("all");
    setLocation("all");
    setJobType("all");
  }

  async function loadTracker(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as unknown;
      const nextApplications = normalizeTracker(parsed);
      setApplications(nextApplications);
      setSourceLabel(`${file.name} · local preview · ${nextApplications.length} records`);
      setError("");
      resetFilters();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The tracker could not be read.");
    } finally {
      event.target.value = "";
    }
  }

  return (
    <main className="command-center">
      <header className="masthead">
        <div className="brand-block">
          <div className="issue-mark"><span>FIELD</span><strong>01</strong></div>
          <div><p className="eyebrow">PRIVATE JOB-SEARCH INTELLIGENCE</p><h1>The application<br /><em>command center.</em></h1></div>
        </div>
        <aside className="hosted-meta">
          <div><span>HOSTED SAFE MODE</span><strong>PRIVATE SITES EDITION</strong></div>
          <button type="button" onClick={() => inputRef.current?.click()}>Preview local tracker</button>
          <input ref={inputRef} className="visually-hidden" type="file" accept="application/json,.json" onChange={loadTracker} />
        </aside>
      </header>

      <div className="privacy-note">
        <strong>Private database connected.</strong>
        <span>Complete sanitized application details are stored; credential identifiers and browser, signature, confirmation, and evidence payloads stay excluded.</span>
      </div>
      {error && <p className="error" role="alert">{error}</p>}

      <nav className="tabs" aria-label="Dashboard sections">
        <button aria-current={tab === "overview" ? "page" : undefined} className={tab === "overview" ? "active" : ""} onClick={() => setTab("overview")}>Overview</button>
        <button aria-current={tab === "applications" ? "page" : undefined} className={tab === "applications" ? "active" : ""} onClick={() => setTab("applications")}>Applications <b>{applications.length}</b></button>
        <button aria-current={tab === "vault" ? "page" : undefined} className={tab === "vault" ? "active" : ""} onClick={() => setTab("vault")}>Account Vault</button>
        <span>{sourceLabel}</span>
      </nav>

      {tab !== "vault" && (
        <>
          <button className="filter-toggle" type="button" aria-expanded={filtersOpen} aria-controls="application-filters" onClick={() => setFiltersOpen((open) => !open)}>
            <span>{filtersOpen ? "Hide filters" : "Search & filter"}</span><strong>{filtered.length} records</strong>
          </button>
          <section id="application-filters" className={`filters ${filtersOpen ? "open" : ""}`} aria-label="Application filters">
            <label className="search"><span>Search</span><input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Company, role, reason…" /></label>
            <label><span>Automation</span><select value={status} onChange={(event) => setStatus(event.target.value)}><option value="all">All outcomes</option><option value="submitted">Submitted</option><option value="blocked">Blocked</option><option value="skipped">Skipped</option><option value="in_progress">In progress</option></select></label>
            <label><span>Job type</span><select value={jobType} onChange={(event) => setJobType(event.target.value)}><option value="all">All job types</option>{jobTypes.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label><span>Source</span><select value={source} onChange={(event) => setSource(event.target.value)}><option value="all">All sources</option>{sources.map((item) => <option key={item}>{item}</option>)}</select></label>
            <label><span>Location</span><select value={location} onChange={(event) => setLocation(event.target.value)}><option value="all">All locations</option>{locations.map((item) => <option key={item}>{item}</option>)}</select></label>
            <strong>{filtered.length} records</strong>
          </section>
        </>
      )}

      {tab === "overview" && (
        <>
          <section className="kpis" aria-label="Application metrics">
            <article className="blue"><span>Tracked attempts</span><strong>{filtered.length}</strong><small>Current filtered view</small></article>
            <article><span>Submission yield</span><strong>{yieldRate.toFixed(1)}%</strong><small>Submitted ÷ final attempts</small></article>
            <article className="orange"><span>Confirmed submissions</span><strong>{submitted}</strong><small>Employer pipeline entries</small></article>
            <article><span>Blocked</span><strong>{filtered.filter((item) => item.status === "blocked").length}</strong><small>Open a record to see why</small></article>
            <article className="olive"><span>Job types</span><strong>{new Set(filtered.map((item) => item.jobType)).size}</strong><small>Role-title classification</small></article>
          </section>
          <section className="chart-grid">
            <article className="panel wide"><div className="panel-head"><h2>Automation outcomes</h2><span>FINAL TRACKER STATE</span></div><BarList rows={outcomeRows} color="orange" /></article>
            <article className="panel"><div className="panel-head"><h2>Job type breakdown</h2><span>INFERRED FROM ROLE TITLES</span></div><BarList rows={jobTypeRows} color="orange" /></article>
            <article className="panel"><div className="panel-head"><h2>Source performance</h2><span>SUBMISSIONS BY SOURCE</span></div><BarList rows={sourceRows.length ? sourceRows : [["No submissions", 0]]} /></article>
            <article className="panel wide"><div className="panel-head"><h2>Location mix</h2><span>TOP MARKETS</span></div><BarList rows={locationRows} color="olive" /></article>
          </section>
          <section className="attention">
            <div><p className="eyebrow">COMPLETE LEDGER</p><h2>Every application, with its story attached.</h2></div>
            <p>Open any ledger record for its run context, timestamps, tracker notes, safe transition history, inferred job type, and employer-pipeline stage. Blocked and skipped roles show the reason and requested next action.</p>
          </section>
        </>
      )}

      {tab === "applications" && (
        <section className="table-panel">
          <div className="panel-head"><h2>Application ledger</h2><span>ALL {filtered.length} FILTERED RECORDS · READ ONLY</span></div>
          <div className="table-scroll">
            <table className="application-table">
              <colgroup>
                <col className="column-application" />
                <col className="column-status" />
                <col className="column-type" />
                <col className="column-location" />
                <col className="column-source" />
                <col className="column-date" />
                <col className="column-record" />
              </colgroup>
              <thead><tr><th>Company / role</th><th>Status / reason</th><th>Job type</th><th>Location</th><th>Source</th><th>Submitted / recorded</th><th>Record</th></tr></thead>
              <tbody>{filtered.map((item) => (
                <tr key={item.id}>
                  <td className="application-cell" data-label="Application">
                    <div className="application-primary"><strong>{item.company}</strong><span>{item.title}</span></div>
                  </td>
                  <td className="status-cell" data-label="Status / reason">
                    <div className="status-stack"><b className={`status ${item.status}`}>{humanize(item.status)}</b>{item.reasonCode && <code>{humanize(item.reasonCode)}</code>}</div>
                  </td>
                  <td className="job-type-cell" data-label="Job type">{item.jobType}</td>
                  <td className="location-cell" data-label="Location">{item.location}</td>
                  <td className="source-cell" data-label="Source">{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.site}</a> : item.site}</td>
                  <td className="date-cell" data-label="Submitted / recorded">{formatDate(item.submittedAt || item.recordedAt)}</td>
                  <td className="record-cell" data-label="Record"><button className="detail-button" type="button" onClick={() => setSelectedApplication(item)}>View details</button></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
          {!filtered.length && <p className="table-note">No applications match these filters.</p>}
        </section>
      )}

      {tab === "vault" && (
        <section className="vault-panel">
          <div className="vault-stamp">LOCAL<br />ONLY</div><p className="eyebrow">OS CREDENTIAL BRIDGE</p><h2>Account Vault stays on your computer.</h2>
          <p>The hosted site cannot reach the operating-system credential vault and will never ask for, receive, or store a password. Start the local dashboard with its per-launch vault command to copy credentials through the protected bridge.</p>
          <div className="vault-rule"><span>Passwords displayed</span><strong>Never</strong><span>Remote fallback</span><strong>Disabled</strong><span>Hosted credential actions</span><strong>0</strong></div>
        </section>
      )}

      <footer><span>PRIVATE JOB-SEARCH COMMAND CENTER</span><span>OWNER-ONLY · SANITIZED APPLICATION DATA · NO CREDENTIAL ACCESS</span></footer>
      {selectedApplication && <ApplicationDetails application={selectedApplication} onClose={() => setSelectedApplication(null)} />}
    </main>
  );
}
