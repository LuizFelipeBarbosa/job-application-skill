"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { AccountVault } from "@/components/account-vault";
import { AnalyticsPanels } from "@/components/analytics-panels";
import { ApplicationFilters } from "@/components/application-filters";
import { ApplicationWorkspace } from "@/components/application-workspace";
import { LockIcon, RefreshIcon } from "@/components/icons";
import { formatDateTime } from "@/lib/format";
import { EMPTY_FILTERS, filterApplications } from "@/lib/metrics";
import type { DashboardFilters, DashboardPayload } from "@/lib/types";
import styles from "./dashboard.module.css";

type DashboardAppProps = {
  initialData: DashboardPayload;
};

type DashboardTab = "overview" | "applications" | "accounts";

export function DashboardApp({ initialData }: DashboardAppProps) {
  const [data, setData] = useState(initialData);
  const [filters, setFilters] = useState<DashboardFilters>(EMPTY_FILTERS);
  const [activeTab, setActiveTab] = useState<DashboardTab>("overview");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState("");

  const refresh = useCallback(async (showBusy = false) => {
    if (showBusy) setRefreshing(true);
    setRefreshError("");
    try {
      const response = await fetch("/api/dashboard", { cache: "no-store" });
      const result = (await response.json()) as DashboardPayload & { error?: string };
      if (!response.ok) throw new Error(result.error || "The dashboard could not refresh.");
      setData(result);
    } catch (error) {
      setRefreshError(error instanceof Error ? error.message : "The dashboard could not refresh.");
    } finally {
      if (showBusy) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => void refresh(false), 15_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const filteredApplications = useMemo(
    () => filterApplications(data.applications, filters, data.timezone),
    [data.applications, data.timezone, filters],
  );

  return (
    <main className={styles.commandCenter}>
      <div className={styles.paperGrain} aria-hidden="true" />
      <header className={styles.masthead}>
        <div className={styles.brandBlock}>
          <div className={styles.issueMark}>
            <span>FIELD</span>
            <strong>01</strong>
          </div>
          <div>
            <span className={styles.eyebrow}>Private job-search intelligence</span>
            <h1>
              The application
              <br />
              <em>command center.</em>
            </h1>
          </div>
        </div>

        <div className={styles.mastheadMeta}>
          <div className={styles.localBadge}>
            <LockIcon />
            <span>
              Local only
              <small>127.0.0.1</small>
            </span>
          </div>
          <div className={styles.freshness}>
            <span>Tracker updated</span>
            <time dateTime={data.freshness.tracker}>
              {formatDateTime(data.freshness.tracker, data.timezone)}
            </time>
          </div>
          <button
            aria-label="Refresh dashboard"
            className={styles.refreshButton}
            disabled={refreshing}
            onClick={() => void refresh(true)}
            type="button"
          >
            <RefreshIcon className={refreshing ? styles.spinning : undefined} />
            {refreshing ? "Refreshing" : "Refresh"}
          </button>
        </div>
      </header>

      <nav aria-label="Dashboard sections" className={styles.tabBar}>
        {([
          ["overview", "Overview"],
          ["applications", "Applications"],
          ["accounts", "Account Vault"],
        ] as const).map(([tab, label]) => (
          <button
            aria-current={activeTab === tab ? "page" : undefined}
            className={activeTab === tab ? styles.activeTab : undefined}
            key={tab}
            onClick={() => setActiveTab(tab)}
            type="button"
          >
            {label}
            {tab === "applications" ? <span>{filteredApplications.length}</span> : null}
          </button>
        ))}
        <div className={styles.tabRule} />
        <span className={styles.snapshotStamp}>Snapshot {formatDateTime(data.generatedAt, data.timezone)}</span>
      </nav>

      {refreshError ? <p className={styles.globalError}>{refreshError}</p> : null}
      {data.warnings.length ? (
        <aside className={styles.warningStrip}>
          <strong>Source note</strong>
          <span>{data.warnings.join(" ")}</span>
        </aside>
      ) : null}

      {activeTab !== "accounts" ? (
        <ApplicationFilters
          filters={filters}
          onChange={setFilters}
          options={data.filterOptions}
          resultCount={filteredApplications.length}
        />
      ) : null}

      {activeTab === "overview" ? (
        <AnalyticsPanels
          applications={filteredApplications}
          runs={data.runs}
          timeZone={data.timezone}
          totalApplications={data.applications.length}
        />
      ) : null}

      {activeTab === "applications" ? (
        <ApplicationWorkspace
          applications={filteredApplications}
          onUpdated={() => refresh(true)}
          timeZone={data.timezone}
        />
      ) : null}

      {activeTab === "accounts" ? <AccountVault timeZone={data.timezone} /> : null}

      <footer className={styles.siteFooter}>
        <span>JOB SEARCH / FIELD NOTES</span>
        <p>
          Private tracker data stays on this machine. Passwords stay in the operating-system vault.
        </p>
        <span>{new Date().getFullYear()}</span>
      </footer>
    </main>
  );
}
