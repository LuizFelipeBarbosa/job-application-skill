import { NextResponse } from "next/server";

import { buildDashboardSnapshot, DashboardDataError } from "@/lib/data.server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET() {
  try {
    return NextResponse.json(await buildDashboardSnapshot(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const message =
      error instanceof DashboardDataError
        ? error.message
        : "The dashboard data could not be loaded.";
    return NextResponse.json({ error: message }, { status: 503 });
  }
}
