"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { formatDate, formatDateTime, formatInteger, formatPercent, humanize } from "@/lib/format";
import {
  buildAttentionQueue,
  buildAutomationBreakdown,
  buildCadence,
  buildLocationBreakdown,
  buildSourcePerformance,
  buildStageBreakdown,
  calculateMetrics,
} from "@/lib/metrics";
import type { DashboardApplication, DashboardRun } from "@/lib/types";
import styles from "./dashboard.module.css";

const COLORS = {
  ink: "#171714",
  cobalt: "#1f4bff",
  cobaltOpen: "#b9c6ff",
  orange: "#f15a32",
  orangeOpen: "#f6b39d",
  olive: "#6d774b",
  gold: "#c89419",
  pink: "#cc6f86",
  stone: "#c9c2b5",
};

const TOOLTIP_STYLE = {
  background: "#fffdf7",
  border: "1px solid #171714",
  borderRadius: 0,
  boxShadow: "4px 4px 0 rgba(23, 23, 20, 0.12)",
  fontFamily: "IBM Plex Sans Variable, sans-serif",
  fontSize: 12,
};

type AnalyticsPanelsProps = {
  applications: DashboardApplication[];
  runs: DashboardRun[];
  timeZone: string;
  totalApplications: number;
};

function ChartHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <header className={styles.chartHeader}>
      <h3>{title}</h3>
      <p>{subtitle}</p>
    </header>
  );
}

function EmptyChart() {
  return <div className={styles.emptyChart}>No records match the active filters.</div>;
}

export function AnalyticsPanels({
  applications,
  runs,
  timeZone,
  totalApplications,
}: AnalyticsPanelsProps) {
  const metrics = calculateMetrics(applications);
  const cadence = buildCadence(applications, timeZone);
  const stages = buildStageBreakdown(applications);
  const automation = buildAutomationBreakdown(applications);
  const sources = buildSourcePerformance(applications);
  const locations = buildLocationBreakdown(applications);
  const attention = buildAttentionQueue(applications);
  const stageColors = [
    COLORS.cobalt,
    COLORS.cobaltOpen,
    COLORS.orange,
    COLORS.gold,
    COLORS.olive,
    COLORS.stone,
    COLORS.pink,
  ];
  const runRows = runs
    .map((run) => {
      const matching = applications.filter((application) => application.runId === run.id);
      return {
        ...run,
        visible: matching.length,
        visibleSubmitted: matching.filter((application) => application.automationStatus === "submitted").length,
        visibleBlocked: matching.filter((application) => application.automationStatus === "blocked").length,
        visibleSkipped: matching.filter((application) => application.automationStatus === "skipped").length,
      };
    })
    .filter((run) => run.visible > 0);

  const cards = [
    {
      label: "Confirmed submissions",
      value: formatInteger(metrics.submitted),
      note: `${formatInteger(applications.length)} filtered records`,
      tone: "blue",
    },
    {
      label: "Submission yield",
      value: formatPercent(metrics.submissionYield),
      note: "Submitted ÷ final tracked attempts",
      tone: "ink",
    },
    {
      label: "Active pipeline",
      value: formatInteger(metrics.activePipeline),
      note: "Applied through offer",
      tone: "orange",
    },
    {
      label: "Employer response",
      value: formatPercent(metrics.responseRate),
      note: "Known responses ÷ submissions",
      tone: "ink",
    },
    {
      label: "Reached interview",
      value: formatInteger(metrics.interviews),
      note: "Ever reached interview or later",
      tone: "olive",
    },
    {
      label: "Reached offer",
      value: formatInteger(metrics.offers),
      note: "Ever reached offer or accepted",
      tone: "gold",
    },
    {
      label: "Follow-ups overdue",
      value: formatInteger(metrics.overdueFollowUps),
      note: "Open actions due now",
      tone: metrics.overdueFollowUps ? "orange" : "ink",
    },
  ];

  return (
    <div className={styles.overviewStack}>
      <section className={styles.kpiGrid} aria-label="Application summary">
        {cards.map((card, index) => (
          <article
            className={`${styles.kpiCard} ${styles[`tone${card.tone.charAt(0).toUpperCase()}${card.tone.slice(1)}`]}`}
            key={card.label}
            style={{ "--reveal-index": index } as React.CSSProperties}
          >
            <span>{card.label}</span>
            <strong>{card.value}</strong>
            <small>{card.note}</small>
          </article>
        ))}
      </section>

      <section className={styles.chartGrid}>
        <article className={`${styles.chartCard} ${styles.chartWide}`}>
          <ChartHeader
            title="Application cadence"
            subtitle={`${humanize(cadence.grain)} buckets · tracked attempts and confirmed submissions`}
          />
          {cadence.points.length ? (
            <div className={styles.chartBody} aria-label="Application cadence chart">
              <ResponsiveContainer height="100%" width="100%">
                <BarChart accessibilityLayer data={cadence.points} margin={{ left: -18, right: 8, top: 8 }}>
                  <CartesianGrid stroke="#ded8cb" strokeDasharray="2 4" vertical={false} />
                  <XAxis
                    axisLine={{ stroke: COLORS.ink }}
                    dataKey="label"
                    interval={cadence.points.length > 12 ? 1 : 0}
                    tick={{ fill: COLORS.ink, fontSize: 10 }}
                    tickLine={false}
                  />
                  <YAxis
                    allowDecimals={false}
                    axisLine={false}
                    tick={{ fill: COLORS.ink, fontSize: 10 }}
                    tickLine={false}
                  />
                  <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "rgba(31,75,255,0.06)" }} />
                  <Legend iconType="square" wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                  <Bar dataKey="tracked" fill={COLORS.stone} isAnimationActive={false} name="All tracked" />
                  <Bar dataKey="submitted" fill={COLORS.cobalt} isAnimationActive={false} name="Submitted" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyChart />
          )}
        </article>

        <article className={styles.chartCard}>
          <ChartHeader
            title="Career stage"
            subtitle="Current stage for confirmed submissions"
          />
          {metrics.submitted ? (
            <div className={styles.chartBody} aria-label="Career stage chart">
              <ResponsiveContainer height="100%" width="100%">
                <BarChart
                  accessibilityLayer
                  data={stages}
                  layout="vertical"
                  margin={{ bottom: 6, left: 8, right: 18, top: 8 }}
                >
                  <CartesianGrid horizontal={false} stroke="#ded8cb" strokeDasharray="2 4" />
                  <XAxis
                    allowDecimals={false}
                    axisLine={{ stroke: COLORS.ink }}
                    tick={{ fill: COLORS.ink, fontSize: 10 }}
                    tickLine={false}
                    type="number"
                  />
                  <YAxis
                    axisLine={false}
                    dataKey="stage"
                    tick={{ fill: COLORS.ink, fontSize: 11 }}
                    tickFormatter={humanize}
                    tickLine={false}
                    type="category"
                    width={74}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    cursor={{ fill: "rgba(31,75,255,0.05)" }}
                    formatter={(value) => [value, "Applications"]}
                    labelFormatter={(label) => humanize(String(label))}
                  />
                  <Bar dataKey="count" isAnimationActive={false} name="Applications">
                    {stages.map((entry, index) => (
                      <Cell fill={stageColors[index]} key={entry.stage} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyChart />
          )}
        </article>

        <article className={styles.chartCard}>
          <ChartHeader
            title="Automation outcomes"
            subtitle="Final tracker state across filtered records"
          />
          {automation.length ? (
            <div className={styles.chartBodySmall} aria-label="Automation outcome chart">
              <ResponsiveContainer height="100%" width="100%">
                <BarChart accessibilityLayer data={automation} layout="vertical" margin={{ left: 12, right: 18 }}>
                  <CartesianGrid horizontal={false} stroke="#ded8cb" strokeDasharray="2 4" />
                  <XAxis
                    allowDecimals={false}
                    axisLine={{ stroke: COLORS.ink }}
                    tick={{ fill: COLORS.ink, fontSize: 10 }}
                    tickLine={false}
                    type="number"
                  />
                  <YAxis
                    axisLine={false}
                    dataKey="status"
                    tick={{ fill: COLORS.ink, fontSize: 11 }}
                    tickFormatter={humanize}
                    tickLine={false}
                    type="category"
                    width={84}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    cursor={{ fill: "rgba(241,90,50,0.05)" }}
                    formatter={(value) => [value, "Records"]}
                    labelFormatter={(label) => humanize(String(label))}
                  />
                  <Bar dataKey="count" fill={COLORS.orange} isAnimationActive={false} name="Records" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyChart />
          )}
        </article>

        <article className={styles.chartCard}>
          <ChartHeader
            title="Source performance"
            subtitle="Top sources ranked by confirmed submissions"
          />
          {sources.length ? (
            <div className={styles.chartBody} aria-label="Source performance chart">
              <ResponsiveContainer height="100%" width="100%">
                <BarChart accessibilityLayer data={sources} layout="vertical" margin={{ left: 12, right: 18 }}>
                  <CartesianGrid horizontal={false} stroke="#ded8cb" strokeDasharray="2 4" />
                  <XAxis
                    allowDecimals={false}
                    axisLine={{ stroke: COLORS.ink }}
                    tick={{ fill: COLORS.ink, fontSize: 10 }}
                    tickLine={false}
                    type="number"
                  />
                  <YAxis
                    axisLine={false}
                    dataKey="site"
                    tick={{ fill: COLORS.ink, fontSize: 10 }}
                    tickLine={false}
                    type="category"
                    width={112}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    cursor={{ fill: "rgba(31,75,255,0.05)" }}
                    formatter={(value, name, item) =>
                      name === "submitted"
                        ? [value, "Submitted"]
                        : [formatPercent(Number(item.payload.yield)), "Yield"]
                    }
                  />
                  <Bar dataKey="submitted" fill={COLORS.cobalt} isAnimationActive={false} name="submitted" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyChart />
          )}
        </article>

        <article className={styles.chartCard}>
          <ChartHeader title="Location mix" subtitle="Top locations among confirmed submissions" />
          {locations.length ? (
            <div className={styles.chartBody} aria-label="Location mix chart">
              <ResponsiveContainer height="100%" width="100%">
                <BarChart accessibilityLayer data={locations} layout="vertical" margin={{ left: 20, right: 18 }}>
                  <CartesianGrid horizontal={false} stroke="#ded8cb" strokeDasharray="2 4" />
                  <XAxis
                    allowDecimals={false}
                    axisLine={{ stroke: COLORS.ink }}
                    tick={{ fill: COLORS.ink, fontSize: 10 }}
                    tickLine={false}
                    type="number"
                  />
                  <YAxis
                    axisLine={false}
                    dataKey="location"
                    tick={{ fill: COLORS.ink, fontSize: 10 }}
                    tickLine={false}
                    type="category"
                    width={118}
                  />
                  <Tooltip
                    contentStyle={TOOLTIP_STYLE}
                    cursor={{ fill: "rgba(109,119,75,0.06)" }}
                    formatter={(value) => [value, "Submissions"]}
                  />
                  <Bar dataKey="count" fill={COLORS.olive} isAnimationActive={false} name="Submissions" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyChart />
          )}
        </article>
      </section>

      <section className={styles.operatingGrid}>
        <article className={styles.operatingCard}>
          <div className={styles.sectionHeading}>
            <div>
              <span className={styles.sectionNumber}>01</span>
              <h3>Attention queue</h3>
            </div>
            <p>Next actions, ordered by due date</p>
          </div>
          {attention.length ? (
            <ol className={styles.attentionList}>
              {attention.map((application) => {
                const overdue =
                  application.nextActionDueAt && new Date(application.nextActionDueAt) <= new Date();
                return (
                  <li key={application.id}>
                    <div>
                      <strong>{application.company}</strong>
                      <span>{application.title}</span>
                    </div>
                    <p>{application.nextAction || "Follow up"}</p>
                    <time className={overdue ? styles.overdue : undefined}>
                      {application.nextActionDueAt
                        ? formatDateTime(application.nextActionDueAt, timeZone)
                        : "No date"}
                    </time>
                  </li>
                );
              })}
            </ol>
          ) : (
            <p className={styles.emptyNote}>No follow-ups are scheduled in this view.</p>
          )}
        </article>

        <article className={styles.operatingCard}>
          <div className={styles.sectionHeading}>
            <div>
              <span className={styles.sectionNumber}>02</span>
              <h3>Application runs</h3>
            </div>
            <p>{applications.length === totalApplications ? "All recorded campaigns" : "Filtered campaign activity"}</p>
          </div>
          {runRows.length ? (
            <div className={styles.runList}>
              {runRows.map((run) => (
                <article key={run.id}>
                  <header>
                    <strong>{run.objective}</strong>
                    <span>{humanize(run.status)}</span>
                  </header>
                  <div className={styles.runProgress}>
                    <span style={{ width: `${Math.min((run.visibleSubmitted / Math.max(run.target, 1)) * 100, 100)}%` }} />
                  </div>
                  <footer>
                    <span>{run.visibleSubmitted} submitted</span>
                    <span>{run.visibleBlocked} blocked</span>
                    <span>{run.visibleSkipped} skipped</span>
                    <span>{formatDate(run.createdAt, timeZone)}</span>
                  </footer>
                </article>
              ))}
            </div>
          ) : (
            <p className={styles.emptyNote}>No application runs match the current filters.</p>
          )}
        </article>
      </section>
    </div>
  );
}
