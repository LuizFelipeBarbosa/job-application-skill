import type {
  CareerStage,
  DashboardApplication,
  DashboardFilters,
  DashboardMetrics,
} from "@/lib/types";

const ACTIVE_STAGES = new Set<CareerStage>(["applied", "screening", "interview", "offer"]);
const RESPONSE_STAGES = new Set<CareerStage>([
  "screening",
  "interview",
  "offer",
  "accepted",
  "rejected",
]);
const INTERVIEW_STAGES = new Set<CareerStage>(["interview", "offer", "accepted"]);
const OFFER_STAGES = new Set<CareerStage>(["offer", "accepted"]);

export const EMPTY_FILTERS: DashboardFilters = {
  search: "",
  runId: "all",
  site: "all",
  location: "all",
  automationStatus: "all",
  careerStage: "all",
  dateFrom: "",
  dateTo: "",
};

type LocalDateParts = { year: number; month: number; day: number; hour: number };

function localDateParts(value: string, timeZone: string): LocalDateParts {
  const parts = new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    hourCycle: "h23",
    timeZone,
  }).formatToParts(new Date(value));
  const part = (type: Intl.DateTimeFormatPartTypes) =>
    Number(parts.find((item) => item.type === type)?.value ?? 0);
  return { year: part("year"), month: part("month"), day: part("day"), hour: part("hour") };
}

function localDateKey(value: string, timeZone: string): string {
  const { year, month, day } = localDateParts(value, timeZone);
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

function dateKeyToUtcDate(key: string): Date {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day, 12));
}

function labelDateKey(key: string): string {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(dateKeyToUtcDate(key));
}

function dateKeysBetween(first: string, last: string): string[] {
  const values: string[] = [];
  const cursor = dateKeyToUtcDate(first);
  const end = dateKeyToUtcDate(last);
  while (cursor <= end) {
    values.push(cursor.toISOString().slice(0, 10));
    cursor.setUTCDate(cursor.getUTCDate() + 1);
  }
  return values;
}

function weekKey(dateKey: string): string {
  const date = dateKeyToUtcDate(dateKey);
  const day = date.getUTCDay();
  date.setUTCDate(date.getUTCDate() - (day === 0 ? 6 : day - 1));
  return date.toISOString().slice(0, 10);
}

function hasReached(application: DashboardApplication, stages: Set<CareerStage>): boolean {
  return application.stageHistory.some((entry) => stages.has(entry.stage));
}

export function filterApplications(
  applications: DashboardApplication[],
  filters: DashboardFilters,
  timeZone: string,
): DashboardApplication[] {
  const search = filters.search.trim().toLowerCase();
  return applications.filter((application) => {
    const searchable = [
      application.company,
      application.title,
      application.location,
      application.site,
      application.nextAction,
    ]
      .join(" ")
      .toLowerCase();
    const dateKey = localDateKey(application.recordedAt, timeZone);
    return (
      (!search || searchable.includes(search)) &&
      (filters.runId === "all" || application.runId === filters.runId) &&
      (filters.site === "all" || application.site === filters.site) &&
      (filters.location === "all" || application.location === filters.location) &&
      (filters.automationStatus === "all" ||
        application.automationStatus === filters.automationStatus) &&
      (filters.careerStage === "all" || application.careerStage === filters.careerStage) &&
      (!filters.dateFrom || dateKey >= filters.dateFrom) &&
      (!filters.dateTo || dateKey <= filters.dateTo)
    );
  });
}

export function calculateMetrics(
  applications: DashboardApplication[],
  now = new Date(),
): DashboardMetrics {
  const submittedApplications = applications.filter(
    (application) => application.automationStatus === "submitted",
  );
  const terminalAttempts = applications.filter((application) =>
    ["submitted", "blocked", "skipped"].includes(application.automationStatus),
  );
  const submitted = submittedApplications.length;
  const activePipeline = submittedApplications.filter(
    (application) => application.careerStage && ACTIVE_STAGES.has(application.careerStage),
  ).length;
  const responses = submittedApplications.filter((application) =>
    hasReached(application, RESPONSE_STAGES),
  ).length;
  const interviews = submittedApplications.filter((application) =>
    hasReached(application, INTERVIEW_STAGES),
  ).length;
  const offers = submittedApplications.filter((application) =>
    hasReached(application, OFFER_STAGES),
  ).length;
  const overdueFollowUps = submittedApplications.filter(
    (application) =>
      application.careerStage &&
      ACTIVE_STAGES.has(application.careerStage) &&
      application.nextActionDueAt &&
      new Date(application.nextActionDueAt) <= now,
  ).length;

  return {
    tracked: applications.length,
    submitted,
    submissionYield: terminalAttempts.length ? submitted / terminalAttempts.length : 0,
    activePipeline,
    responseRate: submitted ? responses / submitted : 0,
    interviews,
    offers,
    overdueFollowUps,
  };
}

export type CadencePoint = {
  key: string;
  label: string;
  tracked: number;
  submitted: number;
};

export function buildCadence(
  applications: DashboardApplication[],
  timeZone: string,
): { grain: "half-day" | "day" | "week"; points: CadencePoint[] } {
  if (!applications.length) {
    return { grain: "day", points: [] };
  }

  const timestamps = applications.map((application) => new Date(application.recordedAt).getTime());
  const durationDays = (Math.max(...timestamps) - Math.min(...timestamps)) / 86_400_000;
  const grain = durationDays <= 7 ? "half-day" : durationDays <= 90 ? "day" : "week";
  const counts = new Map<string, { tracked: number; submitted: number }>();

  for (const application of applications) {
    const dateKey = localDateKey(application.recordedAt, timeZone);
    const parts = localDateParts(application.recordedAt, timeZone);
    const key =
      grain === "half-day"
        ? `${dateKey}-${parts.hour < 12 ? "AM" : "PM"}`
        : grain === "week"
          ? weekKey(dateKey)
          : dateKey;
    const current = counts.get(key) ?? { tracked: 0, submitted: 0 };
    current.tracked += 1;
    current.submitted += Number(application.automationStatus === "submitted");
    counts.set(key, current);
  }

  const dateKeys = applications.map((application) => localDateKey(application.recordedAt, timeZone));
  const first = dateKeys.sort()[0];
  const last = dateKeys.sort().at(-1) ?? first;
  let keys: string[];
  if (grain === "half-day") {
    keys = dateKeysBetween(first, last).flatMap((key) => [`${key}-AM`, `${key}-PM`]);
  } else if (grain === "day") {
    keys = dateKeysBetween(first, last);
  } else {
    keys = [...new Set(dateKeysBetween(first, last).map(weekKey))];
  }

  return {
    grain,
    points: keys.map((key) => {
      const value = counts.get(key) ?? { tracked: 0, submitted: 0 };
      if (grain === "half-day") {
        const period = key.slice(-2);
        return { key, label: `${labelDateKey(key.slice(0, 10))} ${period}`, ...value };
      }
      return { key, label: grain === "week" ? `Week of ${labelDateKey(key)}` : labelDateKey(key), ...value };
    }),
  };
}

export function buildStageBreakdown(applications: DashboardApplication[]) {
  const order: CareerStage[] = [
    "applied",
    "screening",
    "interview",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
  ];
  return order.map((stage) => ({
    stage,
    count: applications.filter((application) => application.careerStage === stage).length,
  }));
}

export function buildAutomationBreakdown(applications: DashboardApplication[]) {
  const order = ["submitted", "blocked", "skipped", "in_progress", "ready_to_submit"];
  return order
    .map((status) => ({
      status,
      count: applications.filter((application) => application.automationStatus === status).length,
    }))
    .filter((item) => item.count > 0);
}

export type SourcePerformance = {
  site: string;
  tracked: number;
  submitted: number;
  blocked: number;
  skipped: number;
  yield: number;
};

export function buildSourcePerformance(applications: DashboardApplication[]): SourcePerformance[] {
  const grouped = new Map<string, SourcePerformance>();
  for (const application of applications) {
    const site = application.site || "Unknown source";
    const current = grouped.get(site) ?? {
      site,
      tracked: 0,
      submitted: 0,
      blocked: 0,
      skipped: 0,
      yield: 0,
    };
    current.tracked += 1;
    current.submitted += Number(application.automationStatus === "submitted");
    current.blocked += Number(application.automationStatus === "blocked");
    current.skipped += Number(application.automationStatus === "skipped");
    grouped.set(site, current);
  }
  return [...grouped.values()]
    .map((item) => ({ ...item, yield: item.tracked ? item.submitted / item.tracked : 0 }))
    .sort((left, right) => right.submitted - left.submitted || right.tracked - left.tracked)
    .slice(0, 8);
}

export function buildLocationBreakdown(applications: DashboardApplication[]) {
  const counts = new Map<string, number>();
  for (const application of applications) {
    if (application.automationStatus !== "submitted") {
      continue;
    }
    const location = application.location || "Location not listed";
    counts.set(location, (counts.get(location) ?? 0) + 1);
  }
  return [...counts.entries()]
    .map(([location, count]) => ({ location, count }))
    .sort((left, right) => right.count - left.count)
    .slice(0, 8);
}

export function buildAttentionQueue(applications: DashboardApplication[]) {
  return applications
    .filter(
      (application) =>
        application.careerStage &&
        ACTIVE_STAGES.has(application.careerStage) &&
        (application.nextAction || application.nextActionDueAt),
    )
    .sort((left, right) => {
      if (!left.nextActionDueAt) return 1;
      if (!right.nextActionDueAt) return -1;
      return left.nextActionDueAt.localeCompare(right.nextActionDueAt);
    })
    .slice(0, 6);
}
