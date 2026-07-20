import { NextRequest, NextResponse } from "next/server";

import { copyAccountPassword, CredentialOperationError } from "@/lib/accounts.server";
import {
  CredentialSecurityError,
  enforceCredentialCopyRateLimit,
  validateCredentialMutation,
} from "@/lib/security.server";

export const runtime = "nodejs";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  try {
    validateCredentialMutation(request);
    enforceCredentialCopyRateLimit();
    const { id } = await context.params;
    return NextResponse.json(await copyAccountPassword(id), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const message =
      error instanceof CredentialSecurityError || error instanceof CredentialOperationError
        ? error.message
        : "The password could not be copied.";
    const status = error instanceof CredentialSecurityError ? error.status : 409;
    return NextResponse.json({ error: message }, { status });
  }
}
