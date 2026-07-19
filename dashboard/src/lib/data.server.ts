import "server-only";

import { readFile, stat } from "node:fs/promises";
import { z } from "zod";

import { calculateMetrics } from "@/lib/metrics";
import {
  outcomesPath,
  successfulApplicationsPath,
  trackerStatePath,
  dashboardTimezone,
} from "@/lib/paths.server";
import {
  OutcomeStoreSchema,
  SuccessfulApplicationsSchema,
  TrackerStateSchema,
} from "@/lib/schemas";
import type {
  DashboardApplication,
  DashboardPayload,
  DashboardRun,
  FilterOptions,
  StageHistoryEntry,
} from "@/lib/types";

export type DashboardSourcePaths = {
  tracker: string;
  successful: string;
  outcomes: string;
};

export class DashboardDataError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DashboardDataError";
  }
}

async function readValidated<T>(filePath: string, schema: z.ZodType<T>): Promise<T> {
  try {
    return schema.parse(JSON.parse(await readFile(filePath, "utf8")));
  } catch (error) {
    if (error instanceof z.ZodError) {
      throw new DashboardDataError(`The dashboard source at ${filePath} has an unsupported shape.`);
    }
    if (error instanceof SyntaxError) {
      throw new DashboardDataError(`The dashboard source at ${filePath} is not valid JSON.`);
    }
    throw error;
  }
}

async function readOptionalValidated<T>(
  filePath: string,
  schema: z.ZodType<T>,
): Promise<{ value: T | null; modifiedAt: string | null }> {
  try {
    const [value, fileStat] = await Promise.all([
      readValidated(filePath, schema),
      stat(filePath),
    ]);
    return { value, modifiedAt: fileStat.mtime.toISOString() };
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return { value: null, modifiedAt: null };
    }
    throw error;
  }
}

export function defaultDashboardSourcePaths(): DashboardSourcePaths {
  return {
    tracker: trackerStatePath(),
    successful: successfulApplicationsPath(),
    outcomes: outcomesPath(),
  };
}

export async function loadTrackerState(filePath = trackerStatePath()) {
  try {
    return await readValidated(filePath, TrackerStateSchema);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      throw new DashboardDataError("The application tracker has not been created yet.");
    }
    throw error;
  }
}

function buildRuns(state: z.infer<typeof TrackerStateSchema>): DashboardRun[] {
  return state.runs.map((run) => ({
    id: run.id,
    objective: run.objective,
    target: run.target,
    status: run.status,
    createdAt: run.created_at,
    completedAt: run.completed_at,
    submitted: run.applications.filter((application) => application.status === "submitted").length,
    blocked: run.applications.filter((application) => application.status === "blocked").length,
    skipped: run.applications.filter((application) => application.status === "skipped").length,
    tracked: run.applications.length,
  }));
}

function buildApplications(
  state: z.infer<typeof TrackerStateSchema>,
  outcomeStore: z.infer<typeof OutcomeStoreSchema> | null,
): DashboardApplication[] {
  return state.runs.flatMap((run) =>
    run.applications.map((application) => {
      const outcome = application.status === "submitted" ? outcomeStore?.applications[application.id] : null;
      const appliedEntry: StageHistoryEntry = { stage: "applied", at: application.recorded_at };
      const storedHistory = outcome?.stage_history ?? [];
      const stageHistory =
        application.status === "submitted"
          ? storedHistory.some((entry) => entry.stage === "applied")
            ? storedHistory
            : [appliedEntry, ...storedHistory]
          : [];

      return {
        id: application.id,
        runId: run.id,
        runObjective: run.objective,
        company: application.company,
        title: application.title,
        location: application.location || "Location not listed",
        site: application.site || "Unknown source",
        url: application.url,
        automationStatus: application.status,
        recordedAt: application.recorded_at,
        updatedAt: application.updated_at ?? application.recorded_at,
        careerStage: application.status === "submitted" ? (outcome?.stage ?? "applied") : null,
        careerStageUpdatedAt:
          application.status === "submitted"
            ? (outcome?.stage_updated_at ?? application.recorded_at)
            : null,
        stageHistory,
        nextAction: outcome?.next_action ?? "",
        nextActionDueAt: outcome?.next_action_due_at ?? null,
        notes: outcome?.notes ?? "",
      };
    }),
  );
}

function buildFilterOptions(
  applications: DashboardApplication[],
  runs: DashboardRun[],
): FilterOptions {
  const unique = (values: string[]) =>
    [...new Set(values)].sort((left, right) => left.localeCompare(right));
  return {
    runs: runs.map((run) => ({ id: run.id, label: run.objective })),
    sites: unique(applications.map((application) => application.site)),
    locations: unique(applications.map((application) => application.location)),
    automationStatuses: [...new Set(applications.map((application) => application.automationStatus))],
    careerStages: [...new Set(applications.flatMap((application) => application.careerStage ?? []))],
  };
}

export async function buildDashboardSnapshot(
  sourcePaths = defaultDashboardSourcePaths(),
): Promise<DashboardPayload> {
  const [state, trackerStat, successful, outcomes] = await Promise.all([
    loadTrackerState(sourcePaths.tracker),
    stat(sourcePaths.tracker),
    readOptionalValidated(sourcePaths.successful, SuccessfulApplicationsSchema),
    readOptionalValidated(sourcePaths.outcomes, OutcomeStoreSchema),
  ]);
  const applications = buildApplications(state, outcomes.value);
  const runs = buildRuns(state);
  const warnings: string[] = [];

  if (successful.value) {
    const trackerSubmitted = new Set(
      applications
        .filter((application) => application.automationStatus === "submitted")
        .map((application) => application.id),
    );
    const projectionSubmitted = new Set(successful.value.applications.map((application) => application.id));
    const missingFromProjection = [...trackerSubmitted].filter((id) => !projectionSubmitted.has(id));
    const extraInProjection = [...projectionSubmitted].filter((id) => !trackerSubmitted.has(id));
    if (missingFromProjection.length || extraInProjection.length) {
      warnings.push(
        `The confirmed-application projection differs from the tracker by ${missingFromProjection.length + extraInProjection.length} record(s).`,
      );
    }
  } else {
    warnings.push("The confirmed-application projection is unavailable; totals use tracker state.");
  }

  const timezone = dashboardTimezone();
  return {
    generatedAt: new Date().toISOString(),
    timezone,
    applications,
    runs,
    metrics: calculateMetrics(applications),
    filterOptions: buildFilterOptions(applications, runs),
    freshness: {
      tracker: trackerStat.mtime.toISOString(),
      successfulProjection: successful.modifiedAt,
      outcomes: outcomes.modifiedAt,
    },
    warnings,
  };
}
