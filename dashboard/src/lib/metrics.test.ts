import { describe, expect, it } from "vitest";

import {
  buildCadence,
  buildSourcePerformance,
  calculateMetrics,
  filterApplications,
  EMPTY_FILTERS,
} from "@/lib/metrics";
import { makeApplication } from "@/test/fixtures";

describe("dashboard metrics", () => {
  const applications = [
    makeApplication({
      id: "applied",
      nextAction: "Follow up",
      nextActionDueAt: "2026-07-15T16:00:00.000Z",
    }),
    makeApplication({
      id: "interview",
      careerStage: "interview",
      stageHistory: [
        { stage: "applied", at: "2026-07-14T17:00:00.000Z" },
        { stage: "screening", at: "2026-07-15T17:00:00.000Z" },
        { stage: "interview", at: "2026-07-16T17:00:00.000Z" },
      ],
    }),
    makeApplication({
      id: "offer",
      careerStage: "offer",
      stageHistory: [
        { stage: "applied", at: "2026-07-14T17:00:00.000Z" },
        { stage: "interview", at: "2026-07-15T17:00:00.000Z" },
        { stage: "offer", at: "2026-07-16T17:00:00.000Z" },
      ],
    }),
    makeApplication({
      id: "rejected",
      careerStage: "rejected",
      stageHistory: [
        { stage: "applied", at: "2026-07-14T17:00:00.000Z" },
        { stage: "rejected", at: "2026-07-15T17:00:00.000Z" },
      ],
    }),
    makeApplication({
      id: "blocked",
      automationStatus: "blocked",
      careerStage: null,
      careerStageUpdatedAt: null,
      stageHistory: [],
    }),
    makeApplication({
      id: "skipped",
      automationStatus: "skipped",
      careerStage: null,
      careerStageUpdatedAt: null,
      stageHistory: [],
    }),
  ];

  it("keeps automation attempts out of the employer pipeline", () => {
    expect(calculateMetrics(applications, new Date("2026-07-18T00:00:00.000Z"))).toEqual({
      tracked: 6,
      submitted: 4,
      submissionYield: 4 / 6,
      activePipeline: 3,
      responseRate: 3 / 4,
      interviews: 2,
      offers: 1,
      overdueFollowUps: 1,
    });
  });

  it("applies search, stage, and local date filters together", () => {
    const filtered = filterApplications(
      [
        makeApplication({ company: "Northstar Labs", careerStage: "screening" }),
        makeApplication({ id: "other", company: "Cedar Systems", recordedAt: "2026-07-20T17:00:00.000Z" }),
      ],
      {
        ...EMPTY_FILTERS,
        search: "northstar",
        careerStage: "screening",
        dateFrom: "2026-07-14",
        dateTo: "2026-07-14",
      },
      "America/Los_Angeles",
    );
    expect(filtered.map((application) => application.company)).toEqual(["Northstar Labs"]);
  });

  it("uses half-day cadence buckets for a short campaign and fills gaps", () => {
    const cadence = buildCadence(
      [
        makeApplication({ recordedAt: "2026-07-14T17:00:00.000Z" }),
        makeApplication({ id: "next", recordedAt: "2026-07-15T23:00:00.000Z" }),
      ],
      "America/Los_Angeles",
    );
    expect(cadence.grain).toBe("half-day");
    expect(cadence.points).toHaveLength(4);
    expect(cadence.points.reduce((total, point) => total + point.submitted, 0)).toBe(2);
  });

  it("ranks sources by confirmed submissions while retaining volume and yield", () => {
    const sources = buildSourcePerformance([
      makeApplication({ id: "one", site: "alpha.example" }),
      makeApplication({ id: "two", site: "alpha.example", automationStatus: "blocked", careerStage: null }),
      makeApplication({ id: "three", site: "beta.example" }),
      makeApplication({ id: "four", site: "beta.example" }),
    ]);
    expect(sources[0]).toMatchObject({ site: "beta.example", submitted: 2, tracked: 2, yield: 1 });
    expect(sources[1]).toMatchObject({ site: "alpha.example", submitted: 1, tracked: 2, yield: 0.5 });
  });
});
