import { copyFile, mkdtemp, readFile, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { describe, expect, it } from "vitest";

import { updateOutcome } from "@/lib/outcomes.server";

describe("outcome storage", () => {
  it("writes a separate private projection atomically and preserves stage history", async () => {
    const directory = await mkdtemp(path.join(os.tmpdir(), "job-outcomes-"));
    const trackerPath = path.join(directory, "application-state.json");
    const outcomePath = path.join(directory, "application-outcomes.json");
    await copyFile(path.resolve("tests/fixtures/tracker-state.fixture.json"), trackerPath);

    await updateOutcome(
      "submitted-two",
      { stage: "interview", notes: "Synthetic note", nextAction: "Prepare", nextActionDueAt: null },
      { trackerPath, outcomePath },
    );
    await updateOutcome("submitted-two", { stage: "offer" }, { trackerPath, outcomePath });

    const stored = JSON.parse(await readFile(outcomePath, "utf8"));
    expect(stored.applications["submitted-two"]).toMatchObject({
      stage: "offer",
      notes: "Synthetic note",
      next_action: "Prepare",
    });
    expect(stored.applications["submitted-two"].stage_history.map((entry: { stage: string }) => entry.stage)).toEqual([
      "applied",
      "interview",
      "offer",
    ]);
    expect((await stat(outcomePath)).mode & 0o777).toBe(0o600);
  });

  it("does not attach employer outcomes to blocked attempts", async () => {
    await expect(
      updateOutcome(
        "blocked-one",
        { stage: "interview" },
        {
          trackerPath: path.resolve("tests/fixtures/tracker-state.fixture.json"),
          outcomePath: path.resolve("tests/fixtures/application-outcomes.json"),
        },
      ),
    ).rejects.toThrow("submitted applications");
  });
});
