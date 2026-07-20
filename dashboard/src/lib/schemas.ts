import { z } from "zod";

import { AUTOMATION_STATUSES, CAREER_STAGES } from "@/lib/types";

const TimestampSchema = z.string().datetime({ offset: true });

export const AutomationStatusSchema = z.enum(AUTOMATION_STATUSES);
export const CareerStageSchema = z.enum(CAREER_STAGES);

export const TrackerApplicationSchema = z
  .object({
    id: z.string().min(1),
    company: z.string().default(""),
    title: z.string().default(""),
    location: z.string().default(""),
    site: z.string().default(""),
    url: z.string().default(""),
    status: AutomationStatusSchema,
    recorded_at: TimestampSchema,
    updated_at: TimestampSchema.optional(),
    transitions: z
      .array(
        z
          .object({
            at: TimestampSchema,
            from: z.string().nullable().optional(),
            to: z.string(),
          })
          .passthrough(),
      )
      .default([]),
  })
  .passthrough();

export const TrackerRunSchema = z
  .object({
    id: z.string().min(1),
    objective: z.string(),
    target: z.number().int().positive(),
    status: z.string(),
    created_at: TimestampSchema,
    completed_at: TimestampSchema.nullable(),
    applications: z.array(TrackerApplicationSchema),
  })
  .passthrough();

export const TrackerStateSchema = z.object({
  schema_version: z.literal(1),
  active_run_id: z.string().nullable(),
  runs: z.array(TrackerRunSchema),
});

export const SuccessfulApplicationsSchema = z.object({
  schema_version: z.literal(1),
  applications: z.array(z.object({ id: z.string(), status: z.literal("submitted") }).passthrough()),
});

export const StageHistoryEntrySchema = z.object({
  stage: CareerStageSchema,
  at: TimestampSchema,
});

export const OutcomeRecordSchema = z.object({
  stage: CareerStageSchema,
  stage_updated_at: TimestampSchema,
  next_action: z.string().max(500).default(""),
  next_action_due_at: TimestampSchema.nullable().default(null),
  notes: z.string().max(5_000).default(""),
  stage_history: z.array(StageHistoryEntrySchema).default([]),
});

export const OutcomeStoreSchema = z.object({
  schema_version: z.literal(1),
  applications: z.record(z.string(), OutcomeRecordSchema),
});

export const OutcomePatchSchema = z
  .object({
    stage: CareerStageSchema.optional(),
    nextAction: z.string().max(500).optional(),
    nextActionDueAt: TimestampSchema.nullable().optional(),
    notes: z.string().max(5_000).optional(),
  })
  .strict()
  .refine((value) => Object.keys(value).length > 0, "At least one field is required.");

const AccountIdentitySchema = z.object({
  site: z.string().min(1),
  username: z.string().min(1),
  created_at: TimestampSchema,
  updated_at: TimestampSchema,
});

const LegacyAccountsFileSchema = z.object({
  schema_version: z.literal(1),
  accounts: z.array(AccountIdentitySchema.extend({ permission_confirmed_at: TimestampSchema })),
});

const CurrentAccountsFileSchema = z.object({
  schema_version: z.literal(2),
  accounts: z.array(
    AccountIdentitySchema.extend({
      authorization: z.object({
        mode: z.enum(["bounded_run", "manual", "legacy_import"]),
        reference: z.string(),
        confirmed_at: TimestampSchema,
      }),
    }),
  ),
});

export const AccountsFileSchema = z.discriminatedUnion("schema_version", [
  LegacyAccountsFileSchema,
  CurrentAccountsFileSchema,
]);
