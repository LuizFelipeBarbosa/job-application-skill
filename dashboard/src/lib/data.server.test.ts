import path from "node:path";
import { mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";

import { describe, expect, it } from "vitest";

import { buildDashboardSnapshot, DashboardDataError } from "@/lib/data.server";

const fixtures = path.resolve("tests/fixtures");

describe("dashboard source adapter", () => {
  it("joins outcome data and returns only the sanitized application contract", async () => {
    const snapshot = await buildDashboardSnapshot({
      tracker: path.join(fixtures, "tracker-state.fixture.json"),
      successful: path.join(fixtures, "successful.fixture.json"),
      outcomes: path.join(fixtures, "application-outcomes.json"),
    });
    expect(snapshot.metrics).toMatchObject({ tracked: 4, submitted: 2 });
    expect(snapshot.warnings).toEqual([]);
    expect(snapshot.applications.find((application) => application.id === "submitted-one")).toMatchObject({
      careerStage: "screening",
      nextAction: "Prepare for recruiter screen",
    });
    expect(snapshot.applications.find((application) => application.id === "submitted-two")).toMatchObject({
      careerStage: "applied",
      stageHistory: [{ stage: "applied", at: "2026-07-15T18:00:00+00:00" }],
    });

    const serialized = JSON.stringify(snapshot.applications);
    for (const forbidden of [
      "confirmation",
      "evidence_refs",
      "document_signatures",
      "profile_signature",
      "browser_session",
      "worker",
    ]) {
      expect(serialized).not.toContain(forbidden);
    }
  });

  it("rejects invalid tracker JSON without exposing its contents", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "job-dashboard-"));
    const invalidPath = path.join(directory, "state.json");
    await writeFile(invalidPath, "{ private invalid value", "utf8");
    await expect(
      buildDashboardSnapshot({
        tracker: invalidPath,
        successful: path.join(directory, "missing-successful.json"),
        outcomes: path.join(directory, "missing-outcomes.json"),
      }),
    ).rejects.toEqual(expect.any(DashboardDataError));
  });
});
