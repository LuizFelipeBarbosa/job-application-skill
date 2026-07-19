import { mkdir, rm } from "node:fs/promises";
import path from "node:path";

import { expect, test } from "@playwright/test";

const outcomePath = path.resolve(".test-runtime/application-outcomes.json");

test.beforeAll(async () => {
  await mkdir(path.dirname(outcomePath), { recursive: true });
  await rm(outcomePath, { force: true });
});

test("renders the source-backed overview and application filters", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /command center/i })).toBeVisible();
  await expect(page.getByText("Confirmed submissions", { exact: true })).toBeVisible();
  await expect(page.getByText("Application cadence")).toBeVisible();
  await expect(page.getByLabel("Application filters")).toBeVisible();

  await page.getByRole("button", { name: /Applications\s*4/i }).click();
  await page.getByLabel("Search applications").fill("Northstar");
  await expect(page.getByText("Northstar Labs", { exact: true })).toBeVisible();
  await expect(page.getByText("Cedar Systems", { exact: true })).toHaveCount(0);
});

test("records an employer outcome in the separate dashboard store", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Applications\s*4/i }).click();
  await page.getByRole("button", { name: "Edit outcome for Northstar Labs" }).click();
  const outcomeDialog = page.getByRole("dialog");
  await outcomeDialog.getByLabel("Career stage").selectOption("interview");
  await outcomeDialog.getByLabel("Next action").fill("Prepare interview stories");
  await outcomeDialog.getByRole("button", { name: "Save field note" }).click();

  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator('[data-stage="interview"]')).toBeVisible();
});

test("keeps Account Vault copy-only in the browser", async ({ page }) => {
  await page.route("**/api/accounts**", async (route) => {
    if (route.request().url().includes("copy-password")) {
      await route.fulfill({
        contentType: "application/json",
        body: JSON.stringify({ copied: true, clearAfterSeconds: 30 }),
      });
      return;
    }
    await route.fulfill({
      contentType: "application/json",
      body: JSON.stringify({
        accounts: [
          {
            id: "opaque-account",
            site: "careers.example.com",
            username: "candidate@example.com",
            createdAt: "2026-07-14T17:00:00.000Z",
            updatedAt: "2026-07-15T17:00:00.000Z",
            loginUrl: "https://careers.example.com/",
          },
        ],
        csrfToken: "e2e-csrf-token",
        vaultAvailable: true,
        vaultMessage: "Secure OS vault connected",
      }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Account Vault" }).click();
  await expect(page.getByText("candidate@example.com")).toBeVisible();
  await page.getByRole("button", { name: "Copy password" }).click();
  await expect(page.getByText("Password copied from the OS vault. Paste it now.")).toBeVisible();
  await expect(page.locator("input[type=password]")).toHaveCount(0);
});

test("matches the editorial overview at desktop and mobile widths", async ({ page }) => {
  await rm(outcomePath, { force: true });
  await page.goto("/");
  await expect(page.getByText("Application cadence")).toBeVisible();
  await expect(page).toHaveScreenshot("overview.png", {
    animations: "disabled",
    fullPage: true,
    maxDiffPixelRatio: 0.01,
  });
});
