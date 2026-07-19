import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AccountVault } from "@/components/account-vault";

describe("Account Vault", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requests a server-side password copy without receiving or sending plaintext", async () => {
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
    const [url, request] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/accounts/opaque-account-id/copy-password");
    expect(request).toMatchObject({ method: "POST", body: "{}" });
    expect(request.headers).toEqual({
      "Content-Type": "application/json",
      "X-Job-Dashboard-CSRF": "csrf-token",
    });
  });
});
