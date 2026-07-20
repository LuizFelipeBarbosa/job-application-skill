import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AccountVault } from "@/components/account-vault";

describe("Account Vault", () => {
  afterEach(() => {
    cleanup();
    window.sessionStorage.clear();
    window.history.replaceState(null, "", "/");
    vi.unstubAllGlobals();
  });

  it("requests a server-side password copy without receiving or sending plaintext", async () => {
    window.sessionStorage.setItem("job_dashboard_vault_token", "launch-token");
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          accounts: [
            {
              id: "opaque-account-id",
              site: "careers.example.com",
              username: "candidate@example.com",
              createdAt: "2026-07-14T17:00:00.000Z",
              updatedAt: "2026-07-15T17:00:00.000Z",
              loginUrl: "https://careers.example.com/",
            },
          ],
          csrfToken: "csrf-token",
          vaultAvailable: true,
          vaultMessage: "Secure OS vault connected",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ copied: true, clearAfterSeconds: 30 }),
      });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<AccountVault timeZone="America/Los_Angeles" />);
    const copyButton = await screen.findByRole("button", { name: "Copy password" });
    await user.click(copyButton);

    await waitFor(() => expect(screen.getByText("Password copied from the OS vault. Paste it now.")).toBeInTheDocument());
    expect(fetchMock.mock.calls[0][1]).toMatchObject({
      headers: { Authorization: "Bearer launch-token" },
    });
    const [url, request] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/accounts/opaque-account-id/copy-password");
    expect(request).toMatchObject({ method: "POST", body: "{}" });
    expect(request.headers).toEqual({
      Authorization: "Bearer launch-token",
      "Content-Type": "application/json",
      "X-Job-Dashboard-CSRF": "csrf-token",
    });
    expect(JSON.stringify(fetchMock.mock.calls)).not.toContain("secret-value");
  });

  it("does not contact credential APIs without a per-launch token", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    render(<AccountVault timeZone="America/Los_Angeles" />);
    expect(await screen.findByText("Disabled for this launch")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("moves a fragment token into tab storage and removes it from the address", async () => {
    window.history.replaceState(null, "", "/#vault_token=fragment-token");
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        accounts: [],
        csrfToken: "csrf-token",
        vaultAvailable: true,
        vaultMessage: "Secure OS vault connected",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<AccountVault timeZone="UTC" />);
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(window.location.hash).toBe("");
    expect(window.sessionStorage.getItem("job_dashboard_vault_token")).toBe("fragment-token");
  });

  it("forgets a token rejected by a later non-vault launch", async () => {
    window.sessionStorage.setItem("job_dashboard_vault_token", "expired-token");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({ error: "Account Vault is disabled." }),
      }),
    );
    render(<AccountVault timeZone="UTC" />);
    expect(await screen.findByText("Disabled for this launch")).toBeInTheDocument();
    expect(window.sessionStorage.getItem("job_dashboard_vault_token")).toBeNull();
  });
});
