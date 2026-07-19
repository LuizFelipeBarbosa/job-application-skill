"use client";

import { SearchIcon } from "@/components/icons";
import { EMPTY_FILTERS } from "@/lib/metrics";
import { humanize } from "@/lib/format";
import type { DashboardFilters, FilterOptions } from "@/lib/types";
import styles from "./dashboard.module.css";

type ApplicationFiltersProps = {
  filters: DashboardFilters;
  options: FilterOptions;
  resultCount: number;
  onChange: (filters: DashboardFilters) => void;
};

export function ApplicationFilters({
  filters,
  options,
  resultCount,
  onChange,
}: ApplicationFiltersProps) {
  const setFilter = (key: keyof DashboardFilters, value: string) => {
    onChange({ ...filters, [key]: value });
  };
  const hasFilters = JSON.stringify(filters) !== JSON.stringify(EMPTY_FILTERS);

  return (
    <section className={styles.filterPanel} aria-label="Application filters">
      <div className={styles.searchField}>
        <SearchIcon />
        <input
          aria-label="Search applications"
          onChange={(event) => setFilter("search", event.target.value)}
          placeholder="Search company, title, location…"
          type="search"
          value={filters.search}
        />
      </div>

      <label className={styles.compactField}>
        <span>Run</span>
        <select value={filters.runId} onChange={(event) => setFilter("runId", event.target.value)}>
          <option value="all">All runs</option>
          {options.runs.map((run) => (
            <option key={run.id} value={run.id}>
              {run.label}
            </option>
          ))}
        </select>
      </label>

      <label className={styles.compactField}>
        <span>Automation</span>
        <select
          value={filters.automationStatus}
          onChange={(event) => setFilter("automationStatus", event.target.value)}
        >
          <option value="all">All outcomes</option>
          {options.automationStatuses.map((status) => (
            <option key={status} value={status}>
              {humanize(status)}
            </option>
          ))}
        </select>
      </label>

      <label className={styles.compactField}>
        <span>Career stage</span>
        <select
          value={filters.careerStage}
          onChange={(event) => setFilter("careerStage", event.target.value)}
        >
          <option value="all">All stages</option>
          {options.careerStages.map((stage) => (
            <option key={stage} value={stage}>
              {humanize(stage)}
            </option>
          ))}
        </select>
      </label>

      <details className={styles.moreFilters}>
        <summary>More filters</summary>
        <div className={styles.moreFiltersGrid}>
          <label className={styles.compactField}>
            <span>Source</span>
            <select value={filters.site} onChange={(event) => setFilter("site", event.target.value)}>
              <option value="all">All sources</option>
              {options.sites.map((site) => (
                <option key={site} value={site}>
                  {site}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.compactField}>
            <span>Location</span>
            <select
              value={filters.location}
              onChange={(event) => setFilter("location", event.target.value)}
            >
              <option value="all">All locations</option>
              {options.locations.map((location) => (
                <option key={location} value={location}>
                  {location}
                </option>
              ))}
            </select>
          </label>
          <label className={styles.compactField}>
            <span>From</span>
            <input
              max={filters.dateTo || undefined}
              onChange={(event) => setFilter("dateFrom", event.target.value)}
              type="date"
              value={filters.dateFrom}
            />
          </label>
          <label className={styles.compactField}>
            <span>Through</span>
            <input
              min={filters.dateFrom || undefined}
              onChange={(event) => setFilter("dateTo", event.target.value)}
              type="date"
              value={filters.dateTo}
            />
          </label>
        </div>
      </details>

      <div className={styles.filterSummary}>
        <span>{resultCount.toLocaleString()} records</span>
        {hasFilters ? (
          <button type="button" onClick={() => onChange(EMPTY_FILTERS)}>
            Reset
          </button>
        ) : null}
      </div>
    </section>
  );
}
