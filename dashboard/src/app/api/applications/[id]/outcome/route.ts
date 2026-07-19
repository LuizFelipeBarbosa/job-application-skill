import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

import { updateOutcome } from "@/lib/outcomes.server";
import { OutcomePatchSchema } from "@/lib/schemas";

export const runtime = "nodejs";

export async function PATCH(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await context.params;
    const patch = OutcomePatchSchema.parse(await request.json());
    const outcome = await updateOutcome(id, patch);
    return NextResponse.json({ updated: true, outcome });
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json({ error: "The outcome update is invalid." }, { status: 400 });
    }
    const message = error instanceof Error ? error.message : "The outcome could not be saved.";
    const status = message === "Application not found." ? 404 : 409;
    return NextResponse.json({ error: message }, { status });
  }
}
