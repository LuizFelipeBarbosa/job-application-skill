"use client";

import { useEffect, useMemo, useState } from "react";

import { ArrowUpRightIcon, CloseIcon, EditIcon } from "@/components/icons";
import { formatDate, formatDateTime, humanize } from "@/lib/format";
import { CAREER_STAGES, type DashboardApplication, type OutcomePatch } from "@/lib/types";
import styles from "./dashboard.module.css";

type SortKey = "company" | "title" | "location" | "recordedAt" | "automationStatus" | "careerStage";
type SortDirection = "ascending" | "descending";

type ApplicationWorkspaceProps = {
  applications: DashboardApplication[];
  timeZone: string;
  onUpdated: () => Promise<void>;
};

function toLocalInput(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function compareValues(left: DashboardApplication, right: DashboardApplication, key: SortKey) {
  return String(left[key] ?? "").localeCompare(String(right[key] ?? ""), undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

function SortButton({
  label,
  sortKey,
  activeKey,
  direction,
  onSort,
}: {
  label: string;
  sortKey: SortKey;
  activeKey: SortKey;
  direction: SortDirection;
  onSort: (key: SortKey) => void;
}) {
  const active = sortKey === activeKey;
  return (
    <button
      aria-label={`Sort by ${label}`}
      className={styles.sortButton}
      onClick={() => onSort(sortKey)}
      type="button"
    >
      {label} <span aria-hidden="true">{active ? (direction === "ascending" ? "↑" : "↓") : "↕"}</span>
    </button>
  );
}

function OutcomeDrawer({
  application,
  timeZone,
  onClose,
  onSaved,
}: {
  application: DashboardApplication;
  timeZone: string;
  onClose: () => void;
  onSaved: () => Promise<void>;
}) {
  const [stage, setStage] = useState(application.careerStage ?? "applied");
  const [nextAction, setNextAction] = useState(application.nextAction);
  const [nextActionDueAt, setNextActionDueAt] = useState(toLocalInput(application.nextActionDueAt));
  const [notes, setNotes] = useState(application.notes);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    const patch: OutcomePatch = {
      stage,
      nextAction: nextAction.trim(),
      nextActionDueAt: nextActionDueAt ? new Date(nextActionDueAt).toISOString() : null,
      notes: notes.trim(),
    };
    try {
      const response = await fetch(`/api/applications/${encodeURIComponent(application.id)}/outcome`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      const result = (await response.json()) as { error?: string };
      if (!response.ok) {
        throw new Error(result.error || "The outcome could not be saved.");
      }
      await onSaved();
      onClose();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "The outcome could not be saved.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={styles.drawerBackdrop} role="presentation" onMouseDown={onClose}>
      <aside
        aria-labelledby="outcome-title"
        aria-modal="true"
        className={styles.drawer}
        onMouseDown={(event) => event.stopPropagation()}
        role="dialog"
      >
        <header className={styles.drawerHeader}>
          <div>
            <span className={styles.eyebrow}>Outcome field note</span>
            <h2 id="outcome-title">{application.company}</h2>
            <p>{application.title}</p>
          </div>
          <button aria-label="Close outcome editor" className={styles.iconButton} onClick={onClose} type="button">
            <CloseIcon />
          </button>
        </header>

        <form className={styles.outcomeForm} onSubmit={save}>
          <label>
            <span>Career stage</span>
            <select value={stage} onChange={(event) => setStage(event.target.value as typeof stage)}>
              {CAREER_STAGES.map((option) => (
                <option key={option} value={option}>
                  {humanize(option)}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Next action</span>
            <input
              maxLength={500}
              onChange={(event) => setNextAction(event.target.value)}
              placeholder="Send a follow-up, prep for interview…"
              value={nextAction}
            />
          </label>
          <label>
            <span>Action due</span>
            <input
              onChange={(event) => setNextActionDueAt(event.target.value)}
              type="datetime-local"
              value={nextActionDueAt}
            />
          </label>
          <label>
            <span>Private notes</span>
            <textarea
              maxLength={5_000}
              onChange={(event) => setNotes(event.target.value)}
              placeholder="Interview context, contact details, preparation notes…"
              rows={6}
              value={notes}
            />
          </label>

          {error ? <p className={styles.formError}>{error}</p> : null}
          <div className={styles.formActions}>
            <button className={styles.secondaryButton} onClick={onClose} type="button">
              Cancel
            </button>
            <button className={styles.primaryButton} disabled={saving} type="submit">
              {saving ? "Saving…" : "Save field note"}
            </button>
          </div>
        </form>

        <section className={styles.historySection}>
          <h3>Stage history</h3>
          <ol>
            {application.stageHistory
              .slice()
              .reverse()
              .map((entry, index) => (
                <li key={`${entry.at}-${entry.stage}-${index}`}>
                  <span>{humanize(entry.stage)}</span>
                  <time>{formatDateTime(entry.at, timeZone)}</time>
                </li>
              ))}
          </ol>
        </section>
      </aside>
    </div>
  );
}

export function ApplicationWorkspace({
  applications,
  timeZone,
  onUpdated,
}: ApplicationWorkspaceProps) {
  const [sortKey, setSortKey] = useState<SortKey>("recordedAt");
  const [sortDirection, setSortDirection] = useState<SortDirection>("descending");
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<DashboardApplication | null>(null);
  const pageSize = 20;

  const sorted = useMemo(() => {
    return [...applications].sort((left, right) => {
      const comparison = compareValues(left, right, sortKey);
      return sortDirection === "ascending" ? comparison : -comparison;
    });
  }, [applications, sortDirection, sortKey]);
  const pageCount = Math.max(Math.ceil(sorted.length / pageSize), 1);
  const currentPage = Math.min(page, pageCount);
  const visible = sorted.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const sort = (nextKey: SortKey) => {
    if (nextKey === sortKey) {
      setSortDirection((current) => (current === "ascending" ? "descending" : "ascending"));
    } else {
      setSortKey(nextKey);
      setSortDirection("ascending");
    }
  };

  return (
    <section className={styles.applicationWorkspace}>
      <div className={styles.sectionHeadingLarge}>
        <div>
          <span className={styles.eyebrow}>The complete ledger</span>
          <h2>Applications</h2>
        </div>
        <p>Open a submitted role to record employer outcomes, notes, and the next move.</p>
      </div>

      <div className={styles.tableShell}>
        <table>
          <thead>
            <tr>
              <th><SortButton activeKey={sortKey} direction={sortDirection} label="Company" onSort={sort} sortKey="company" /></th>
              <th><SortButton activeKey={sortKey} direction={sortDirection} label="Role" onSort={sort} sortKey="title" /></th>
              <th><SortButton activeKey={sortKey} direction={sortDirection} label="Location" onSort={sort} sortKey="location" /></th>
              <th><SortButton activeKey={sortKey} direction={sortDirection} label="Automation" onSort={sort} sortKey="automationStatus" /></th>
              <th><SortButton activeKey={sortKey} direction={sortDirection} label="Career" onSort={sort} sortKey="careerStage" /></th>
              <th><SortButton activeKey={sortKey} direction={sortDirection} label="Recorded" onSort={sort} sortKey="recordedAt" /></th>
              <th><span className={styles.srOnly}>Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((application) => (
              <tr key={application.id}>
                <td>
                  <strong>{application.company}</strong>
                  <small>{application.site}</small>
                </td>
                <td>{application.title}</td>
                <td>{application.location}</td>
                <td>
                  <span className={styles.statusPill} data-status={application.automationStatus}>
                    {humanize(application.automationStatus)}
                  </span>
                </td>
                <td>
                  {application.careerStage ? (
                    <span className={styles.stagePill} data-stage={application.careerStage}>
                      {humanize(application.careerStage)}
                    </span>
                  ) : (
                    <span className={styles.muted}>—</span>
                  )}
                </td>
                <td>
                  <time dateTime={application.recordedAt}>{formatDate(application.recordedAt, timeZone)}</time>
                </td>
                <td>
                  <div className={styles.rowActions}>
                    {application.automationStatus === "submitted" ? (
                      <button aria-label={`Edit outcome for ${application.company}`} onClick={() => setSelected(application)} type="button">
                        <EditIcon />
                      </button>
                    ) : null}
                    {application.url ? (
                      <a aria-label={`Open ${application.company} application`} href={application.url} rel="noreferrer" target="_blank">
                        <ArrowUpRightIcon />
                      </a>
                    ) : null}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!visible.length ? <div className={styles.emptyTable}>No applications match the active filters.</div> : null}
      </div>

      <footer className={styles.pagination}>
        <span>
          Page {currentPage} of {pageCount} · {applications.length.toLocaleString()} records
        </span>
        <div>
          <button disabled={currentPage === 1} onClick={() => setPage(currentPage - 1)} type="button">
            Previous
          </button>
          <button disabled={currentPage === pageCount} onClick={() => setPage(currentPage + 1)} type="button">
            Next
          </button>
        </div>
      </footer>

      {selected ? (
        <OutcomeDrawer
          application={selected}
          onClose={() => setSelected(null)}
          onSaved={onUpdated}
          timeZone={timeZone}
        />
      ) : null}
    </section>
  );
}
