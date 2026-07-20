import { NextRequest } from "next/server";
import { afterEach, describe, expect, it } from "vitest";

import {
  CSRF_COOKIE_NAME,
  enforceCredentialCopyRateLimit,
  resetCredentialCopyRateLimitForTests,
  validateCredentialMutation,
} from "@/lib/security.server";

function request(overrides: {
  host?: string;
  origin?: string;
  headerToken?: string;
  cookieToken?: string;
  bearerToken?: string;
  fetchSite?: string;
} = {}) {
  const host = overrides.host ?? "127.0.0.1:3000";
  const origin = overrides.origin ?? "http://127.0.0.1:3000";
  const headerToken = overrides.headerToken ?? "matching-token";
  const cookieToken = overrides.cookieToken ?? "matching-token";
  return new NextRequest(`http://${host}/api/accounts/example/copy-password`, {
    method: "POST",
    headers: {
      host,
      origin,
      "content-type": "application/json",
      "x-job-dashboard-csrf": headerToken,
      authorization: `Bearer ${overrides.bearerToken ?? "launch-token"}`,
      "sec-fetch-site": overrides.fetchSite ?? "same-origin",
      "sec-fetch-mode": "cors",
      cookie: `${CSRF_COOKIE_NAME}=${cookieToken}`,
    },
    body: "{}",
  });
}

describe("credential request security", () => {
  afterEach(() => {
    delete process.env.JOB_DASHBOARD_VAULT_TOKEN;
    resetCredentialCopyRateLimitForTests();
  });

  it("accepts a matching local same-origin session", () => {
    process.env.JOB_DASHBOARD_VAULT_TOKEN = "launch-token";
    expect(() => validateCredentialMutation(request())).not.toThrow();
  });

  it("rejects cross-origin, remote-host, and mismatched-token requests", () => {
    process.env.JOB_DASHBOARD_VAULT_TOKEN = "launch-token";
    expect(() => validateCredentialMutation(request({ origin: "https://malicious.example" }))).toThrow(
      "Cross-origin",
    );
    expect(() =>
      validateCredentialMutation(
        request({ host: "dashboard.example", origin: "http://dashboard.example" }),
      ),
    ).toThrow("restricted to this computer");
    expect(() => validateCredentialMutation(request({ headerToken: "wrong" }))).toThrow(
      "session expired",
    );
    expect(() => validateCredentialMutation(request({ bearerToken: "wrong" }))).toThrow(
      "launch token",
    );
    expect(() => validateCredentialMutation(request({ fetchSite: "cross-site" }))).toThrow(
      "same-origin browser metadata",
    );
  });

  it("limits password copies globally within a one-minute window", () => {
    resetCredentialCopyRateLimitForTests();
    for (let index = 0; index < 5; index += 1) enforceCredentialCopyRateLimit(1_000 + index);
    expect(() => enforceCredentialCopyRateLimit(2_000)).toThrow("rate limit");
    expect(() => enforceCredentialCopyRateLimit(62_000)).not.toThrow();
  });
});
