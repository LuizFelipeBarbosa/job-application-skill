import { NextRequest, NextResponse } from "next/server";

import { clearCredentialClipboard, CredentialOperationError } from "@/lib/accounts.server";
import {
  CredentialSecurityError,
  validateCredentialMutation,
} from "@/lib/security.server";

export const runtime = "nodejs";

export async function POST(request: NextRequest) {
  try {
    validateCredentialMutation(request);
    return NextResponse.json(await clearCredentialClipboard(), {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (error) {
    const message =
      error instanceof CredentialSecurityError || error instanceof CredentialOperationError
        ? error.message
        : "The clipboard could not be cleared.";
    const status = error instanceof CredentialSecurityError ? 403 : 409;
    return NextResponse.json({ error: message }, { status });
  }
}
