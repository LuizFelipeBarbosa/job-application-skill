import { NextRequest, NextResponse } from "next/server";

import { listAccountSummaries, vaultStatus } from "@/lib/accounts.server";
import {
  createCsrfToken,
  CSRF_COOKIE_NAME,
  CredentialSecurityError,
  validateCredentialRead,
} from "@/lib/security.server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: NextRequest) {
  try {
    validateCredentialRead(request);
    const [accounts, vault] = await Promise.all([listAccountSummaries(), vaultStatus()]);
    const csrfToken = createCsrfToken();
    const response = NextResponse.json(
      {
        accounts,
        csrfToken,
        vaultAvailable: vault.available,
        vaultMessage: vault.message,
      },
      { headers: { "Cache-Control": "no-store" } },
    );
    response.cookies.set(CSRF_COOKIE_NAME, csrfToken, {
      httpOnly: true,
      sameSite: "strict",
      secure: false,
      path: "/api",
      maxAge: 60 * 60,
    });
    return response;
  } catch (error) {
    const message =
      error instanceof CredentialSecurityError
        ? error.message
        : "Account Vault could not be loaded.";
    const status = error instanceof CredentialSecurityError ? error.status : 403;
    return NextResponse.json({ error: message }, { status });
  }
}
