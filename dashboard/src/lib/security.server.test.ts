import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { CSRF_COOKIE_NAME, validateCredentialMutation } from "@/lib/security.server";

function request(overrides: { host?: string; origin?: string; headerToken?: string; cookieToken?: string } = {}) {
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
      cookie: `${CSRF_COOKIE_NAME}=${cookieToken}`,
    },
    body: "{}",
  });
}

describe("credential request security", () => {
  it("accepts a matching local same-origin session", () => {
    expect(() => validateCredentialMutation(request())).not.toThrow();
  });

  it("rejects cross-origin, remote-host, and mismatched-token requests", () => {
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
  });
});
