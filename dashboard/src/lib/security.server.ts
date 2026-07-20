import "server-only";

import { randomBytes, timingSafeEqual } from "node:crypto";
import type { NextRequest } from "next/server";

export const CSRF_COOKIE_NAME = "job_dashboard_csrf";
const COPY_LIMIT = 5;
const COPY_WINDOW_MS = 60_000;

let credentialCopyTimes: number[] = [];

export class CredentialSecurityError extends Error {
  constructor(message: string, readonly status = 403) {
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

function assertFetchMetadata(request: NextRequest): void {
  if (request.headers.get("sec-fetch-site") !== "same-origin") {
    throw new CredentialSecurityError("Credential access requires same-origin browser metadata.");
  }
  const mode = request.headers.get("sec-fetch-mode");
  if (mode !== "cors" && mode !== "same-origin") {
    throw new CredentialSecurityError("Credential access requires a browser fetch request.");
  }
}

function bearerToken(request: NextRequest): string {
  const authorization = request.headers.get("authorization") ?? "";
  return authorization.startsWith("Bearer ") ? authorization.slice(7) : "";
}

function configuredVaultToken(): string {
  return process.env.JOB_DASHBOARD_VAULT_TOKEN ?? "";
}

function assertVaultToken(request: NextRequest): void {
  const supplied = bearerToken(request);
  const configured = configuredVaultToken();
  if (!supplied || !configured || !tokensMatch(supplied, configured)) {
    throw new CredentialSecurityError("Account Vault is disabled or this launch token is invalid.");
  }
}

export function validateCredentialRead(request: NextRequest): void {
  assertLocalRequest(request);
  assertFetchMetadata(request);
  assertVaultToken(request);
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
  validateCredentialRead(request);
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

export function enforceCredentialCopyRateLimit(now = Date.now()): void {
  credentialCopyTimes = credentialCopyTimes.filter((timestamp) => now - timestamp < COPY_WINDOW_MS);
  if (credentialCopyTimes.length >= COPY_LIMIT) {
    throw new CredentialSecurityError(
      "Credential copy rate limit reached. Wait one minute before trying again.",
      429,
    );
  }
  credentialCopyTimes.push(now);
}

export function resetCredentialCopyRateLimitForTests(): void {
  if (process.env.NODE_ENV === "test") credentialCopyTimes = [];
}
