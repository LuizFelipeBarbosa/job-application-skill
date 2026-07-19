import "server-only";

import { chmod, mkdir, readFile, rename, unlink, writeFile } from "node:fs/promises";
import path from "node:path";
import { randomUUID } from "node:crypto";

import { loadTrackerState } from "@/lib/data.server";
import { outcomesPath, trackerStatePath } from "@/lib/paths.server";
import { OutcomePatchSchema, OutcomeStoreSchema } from "@/lib/schemas";
import type { OutcomePatch } from "@/lib/types";

type OutcomeStore = ReturnType<typeof OutcomeStoreSchema.parse>;

let writeChain: Promise<void> = Promise.resolve();

async function loadOutcomeStore(filePath: string): Promise<OutcomeStore> {
  try {
    return OutcomeStoreSchema.parse(JSON.parse(await readFile(filePath, "utf8")));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return { schema_version: 1, applications: {} };
    }
    throw error;
  }
}

async function writeJsonAtomic(filePath: string, value: unknown): Promise<void> {
  await mkdir(path.dirname(filePath), { recursive: true });
  const temporaryPath = `${filePath}.${process.pid}.${randomUUID()}.tmp`;
  try {
    await writeFile(temporaryPath, `${JSON.stringify(value, null, 2)}\n`, {
      encoding: "utf8",
      mode: 0o600,
    });
    await chmod(temporaryPath, 0o600);
    await rename(temporaryPath, filePath);
  } finally {
    await unlink(temporaryPath).catch(() => undefined);
  }
}

function enqueueWrite<T>(operation: () => Promise<T>): Promise<T> {
  const result = writeChain.then(operation, operation);
  writeChain = result.then(
    () => undefined,
    () => undefined,
  );
  return result;
}

export async function updateOutcome(
  applicationId: string,
  input: OutcomePatch,
  options: { trackerPath?: string; outcomePath?: string } = {},
) {
  const patch = OutcomePatchSchema.parse(input);
  const trackerPath = options.trackerPath ?? trackerStatePath();
  const outcomePath = options.outcomePath ?? outcomesPath();

  return enqueueWrite(async () => {
    const state = await loadTrackerState(trackerPath);
    const application = state.runs
      .flatMap((run) => run.applications)
      .find((item) => item.id === applicationId);
    if (!application) {
      throw new Error("Application not found.");
    }
    if (application.status !== "submitted") {
      throw new Error("Career outcomes can only be recorded for submitted applications.");
    }

    const store = await loadOutcomeStore(outcomePath);
    const now = new Date().toISOString();
    const current = store.applications[applicationId] ?? {
      stage: "applied" as const,
      stage_updated_at: application.recorded_at,
      next_action: "",
      next_action_due_at: null,
      notes: "",
      stage_history: [{ stage: "applied" as const, at: application.recorded_at }],
    };
    const stageChanged = patch.stage && patch.stage !== current.stage;
    const next = {
      ...current,
      stage: patch.stage ?? current.stage,
      stage_updated_at: stageChanged ? now : current.stage_updated_at,
      next_action: patch.nextAction ?? current.next_action,
      next_action_due_at:
        patch.nextActionDueAt === undefined ? current.next_action_due_at : patch.nextActionDueAt,
      notes: patch.notes ?? current.notes,
      stage_history: stageChanged
        ? [...current.stage_history, { stage: patch.stage!, at: now }]
        : current.stage_history,
    };
    store.applications[applicationId] = next;
    await writeJsonAtomic(outcomePath, store);
    return next;
  });
}
