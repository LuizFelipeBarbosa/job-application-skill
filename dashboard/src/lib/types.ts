export const CAREER_STAGES = [
  "applied",
  "screening",
  "interview",
  "offer",
  "accepted",
  "rejected",
  "withdrawn",
] as const;

export type CareerStage = (typeof CAREER_STAGES)[number];

export const AUTOMATION_STATUSES = [
  "in_progress",
  "blocked",
  "ready_to_submit",
  "submitted",
  "skipped",
] as const;

export type AutomationStatus = (typeof AUTOMATION_STATUSES)[number];

export type StageHistoryEntry = {
  stage: CareerStage;
  at: string;
};

export type DashboardApplication = {
  id: string;
  runId: string;
  runObjective: string;
  company: string;
  title: string;
  location: string;
  site: string;
  url: string;
  automationStatus: AutomationStatus;
  recordedAt: string;
  updatedAt: string;
  careerStage: CareerStage | null;
  careerStageUpdatedAt: string | null;
  stageHistory: StageHistoryEntry[];
  nextAction: string;
  nextActionDueAt: string | null;
  notes: string;
};

export type DashboardRun = {
  id: string;
  objective: string;
  target: number;
  status: string;
  createdAt: string;
  completedAt: string | null;
  submitted: number;
  blocked: number;
  skipped: number;
  tracked: number;
};

export type DashboardMetrics = {
  tracked: number;
  submitted: number;
  submissionYield: number;
  activePipeline: number;
  responseRate: number;
  interviews: number;
  offers: number;
  overdueFollowUps: number;
};

export type FilterOptions = {
  runs: Array<{ id: string; label: string }>;
  sites: string[];
  locations: string[];
  automationStatuses: AutomationStatus[];
  careerStages: CareerStage[];
};

export type DashboardPayload = {
  generatedAt: string;
  timezone: string;
  applications: DashboardApplication[];
  runs: DashboardRun[];
  metrics: DashboardMetrics;
  filterOptions: FilterOptions;
  freshness: {
    tracker: string;
    successfulProjection: string | null;
    outcomes: string | null;
  };
  warnings: string[];
};

export type DashboardFilters = {
  search: string;
  runId: string;
  site: string;
  location: string;
  automationStatus: string;
  careerStage: string;
  dateFrom: string;
  dateTo: string;
};

export type OutcomePatch = {
  stage?: CareerStage;
  nextAction?: string;
  nextActionDueAt?: string | null;
  notes?: string;
};

export type AccountSummary = {
  id: string;
  site: string;
  username: string;
  createdAt: string;
  updatedAt: string;
  loginUrl: string;
};

export type AccountsPayload = {
  accounts: AccountSummary[];
  csrfToken: string;
  vaultAvailable: boolean;
  vaultMessage: string;
};
