import type { CareerStage, DashboardApplication } from "@/lib/types";

export function makeApplication(
  overrides: Partial<DashboardApplication> = {},
): DashboardApplication {
  const careerStage: CareerStage | null = overrides.careerStage ?? "applied";
  return {
    id: "application-1",
    runId: "run-1",
    runObjective: "Synthetic test run",
    company: "Example Company",
    title: "Analyst",
    location: "Remote",
    site: "jobs.example.com",
    url: "https://jobs.example.com/1",
    automationStatus: "submitted",
    recordedAt: "2026-07-14T17:00:00.000Z",
    updatedAt: "2026-07-14T17:00:00.000Z",
    careerStage,
    careerStageUpdatedAt: careerStage ? "2026-07-14T17:00:00.000Z" : null,
    stageHistory: careerStage ? [{ stage: careerStage, at: "2026-07-14T17:00:00.000Z" }] : [],
    nextAction: "",
    nextActionDueAt: null,
    notes: "",
    ...overrides,
  };
}
