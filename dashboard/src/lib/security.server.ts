import "server-only";

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { NextRequest } from "next/server";

export const CSRF_COOKIE_NAME = "job_dashboard_csrf";

export class CredentialSecurityError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CredentialSecurityError";
  }
}

function isLoopbackHostname(hostname: string): boolean {
  return hostname === "127.0.0.1" || hostname === "localhost" || hostname === "[::1]";
}

export function assertLocalRequest(request: NextRequest): void {
  const host = request.headers.get("host");
  if (!host) {
    throw new CredentialSecurityError("Credential access requires a local dashboard host.");
  }
  const hostUrl = new URL(`http://${host}`);
  if (!isLoopbackHostname(hostUrl.hostname)) {
    throw new CredentialSecurityError("Credential access is restricted to this computer.");
  }
}

export function createCsrfToken(): string {
  return randomBytes(32).toString("base64url");
}

function tokensMatch(left: string, right: string): boolean {
  const leftBuffer = Buffer.from(left);
  const rightBuffer = Buffer.from(right);
  return leftBuffer.length === rightBuffer.length && timingSafeEqual(leftBuffer, rightBuffer);
}

export function validateCredentialMutation(request: NextRequest): void {
  assertLocalRequest(request);
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  if (!origin || !host) {
    throw new CredentialSecurityError("Credential access requires a same-origin request.");
  }

  let originUrl: URL;
  try {
    originUrl = new URL(origin);
  } catch {
    throw new CredentialSecurityError("Credential access requires a valid local origin.");
  }
  if (!isLoopbackHostname(originUrl.hostname) || originUrl.host !== host) {
    throw new CredentialSecurityError("Cross-origin credential requests are not allowed.");
  }

  const contentType = request.headers.get("content-type")?.split(";", 1)[0];
  if (contentType !== "application/json") {
    throw new CredentialSecurityError("Credential access requires a JSON request.");
  }

  const headerToken = request.headers.get("x-job-dashboard-csrf") ?? "";
  const cookieToken = request.cookies.get(CSRF_COOKIE_NAME)?.value ?? "";
  if (!headerToken || !cookieToken || !tokensMatch(headerToken, cookieToken)) {
    throw new CredentialSecurityError("The credential session expired. Reload Account Vault.");
  }
}
