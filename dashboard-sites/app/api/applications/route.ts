import { getD1 } from "../../../db";
import { getChatGPTUser } from "../../chatgpt-auth";

export const dynamic = "force-dynamic";

type StatusHistoryEntry = {
  at: string;
  from: string | null;
  to: string;
  reasonCode: string;
};

type StageHistoryEntry = {
  at: string;
  stage: string;
};

type StoredApplication = {
  id: string;
  runId: string;
  runStatus: string;
  runTarget: number;
  runCreatedAt: string;
  runCompletedAt: string;
  company: string;
  title: string;
  jobType: string;
  jobId: string;
  location: string;
  site: string;
  url: string;
  canonicalUrl: string;
  status: string;
  reasonCode: string;
  statusHistoryJson: string;
  createdAt: string;
  recordedAt: string;
  updatedAt: string;
  submittedAt: string;
  generatedAnswerCount: number;
  inferredAnswerCount: number;
  careerStage: string;
  careerStageUpdatedAt: string;
  nextActionDueAt: string;
  stageHistoryJson: string;
  importedAt: string;
};

function parseHistory<T>(value: string): T[] {
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export async function GET() {
  if (!(await getChatGPTUser())) {
    return Response.json(
      { error: "Authentication required." },
      { status: 401, headers: { "Cache-Control": "private, no-store" } },
    );
  }
  try {
    const result = await getD1().prepare(`
      SELECT
        id,
        run_id AS runId,
        run_status AS runStatus,
        run_target AS runTarget,
        run_created_at AS runCreatedAt,
        run_completed_at AS runCompletedAt,
        company,
        title,
        job_type AS jobType,
        job_id AS jobId,
        location,
        site,
        url,
        canonical_url AS canonicalUrl,
        automation_status AS status,
        reason_code AS reasonCode,
        status_history_json AS statusHistoryJson,
        created_at AS createdAt,
        recorded_at AS recordedAt,
        updated_at AS updatedAt,
        submitted_at AS submittedAt,
        generated_answer_count AS generatedAnswerCount,
        inferred_answer_count AS inferredAnswerCount,
        career_stage AS careerStage,
        career_stage_updated_at AS careerStageUpdatedAt,
        next_action_due_at AS nextActionDueAt,
        stage_history_json AS stageHistoryJson,
        imported_at AS importedAt
      FROM applications
      ORDER BY recorded_at DESC, id ASC
    `).all<StoredApplication>();

    const applications = result.results.map(({ statusHistoryJson, stageHistoryJson, ...application }) => ({
      ...application,
      statusHistory: parseHistory<StatusHistoryEntry>(statusHistoryJson),
      stageHistory: parseHistory<StageHistoryEntry>(stageHistoryJson),
    }));
    const snapshotAt = result.results.reduce(
      (latest, application) => application.importedAt > latest ? application.importedAt : latest,
      "",
    );

    return Response.json(
      { applications, snapshotAt },
      { headers: { "Cache-Control": "private, no-store" } },
    );
  } catch {
    return Response.json(
      { error: "The private application store is unavailable." },
      { status: 503, headers: { "Cache-Control": "private, no-store" } },
    );
  }
}
