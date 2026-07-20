import "server-only";

import { createHash } from "node:crypto";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { readFile } from "node:fs/promises";

import { accountsPath, passwordManagerPath, workspaceRoot } from "@/lib/paths.server";
import { AccountsFileSchema } from "@/lib/schemas";
import type { AccountSummary } from "@/lib/types";

const execFileAsync = promisify(execFile);
const CLEAR_AFTER_SECONDS = 30;
let cachedVaultStatus: { available: boolean; message: string; expiresAt: number } | null = null;

export class CredentialOperationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CredentialOperationError";
  }
}

function opaqueAccountId(site: string, username: string): string {
  return createHash("sha256").update(site).update("\0").update(username).digest("hex").slice(0, 24);
}

function safeLoginUrl(site: string): string {
  try {
    const url = new URL(`https://${site}`);
    return url.protocol === "https:" ? url.toString() : "";
  } catch {
    return "";
  }
}

async function loadAccounts(filePath = accountsPath()) {
  try {
    return AccountsFileSchema.parse(JSON.parse(await readFile(filePath, "utf8")));
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return { schema_version: 2 as const, accounts: [] };
    }
    throw new CredentialOperationError("Account metadata could not be loaded.");
  }
}

async function runPasswordManager(argumentsList: string[]): Promise<Record<string, unknown>> {
  const executable = process.env.JOB_DASHBOARD_PYTHON || "python3";
  try {
    const { stdout } = await execFileAsync(
      executable,
      [passwordManagerPath(), "--metadata", accountsPath(), ...argumentsList],
      {
        cwd: workspaceRoot(),
        encoding: "utf8",
        maxBuffer: 64 * 1024,
        timeout: 10_000,
        windowsHide: true,
      },
    );
    const result = JSON.parse(stdout) as Record<string, unknown>;
    if ("password" in result) {
      throw new CredentialOperationError("The password manager returned an unsafe response.");
    }
    return result;
  } catch (error) {
    if (error instanceof CredentialOperationError) {
      throw error;
    }
    throw new CredentialOperationError(
      "The operating-system credential vault is unavailable or denied access.",
    );
  }
}

export async function vaultStatus(): Promise<{ available: boolean; message: string }> {
  if (cachedVaultStatus && cachedVaultStatus.expiresAt > Date.now()) {
    return { available: cachedVaultStatus.available, message: cachedVaultStatus.message };
  }
  try {
    const result = await runPasswordManager(["backend"]);
    const available = result.secure === true;
    cachedVaultStatus = {
      available,
      message: available ? "Secure OS vault connected" : "Secure OS vault unavailable",
      expiresAt: Date.now() + 30_000,
    };
  } catch {
    cachedVaultStatus = {
      available: false,
      message: "Secure OS vault unavailable or permission denied",
      expiresAt: Date.now() + 10_000,
    };
  }
  return { available: cachedVaultStatus.available, message: cachedVaultStatus.message };
}

export async function listAccountSummaries(): Promise<AccountSummary[]> {
  const metadata = await loadAccounts();
  return metadata.accounts
    .map((account) => ({
      id: opaqueAccountId(account.site, account.username),
      site: account.site,
      username: account.username,
      createdAt: account.created_at,
      updatedAt: account.updated_at,
      loginUrl: safeLoginUrl(account.site),
    }))
    .sort((left, right) => right.updatedAt.localeCompare(left.updatedAt));
}

async function findAccount(accountId: string) {
  const metadata = await loadAccounts();
  return metadata.accounts.find(
    (account) => opaqueAccountId(account.site, account.username) === accountId,
  );
}

async function clearClipboardCommand(): Promise<void> {
  const result = await runPasswordManager(["clear-clipboard"]);
  if (result.clipboard_cleared !== true) {
    throw new CredentialOperationError("The clipboard could not be cleared.");
  }
}

export async function copyAccountPassword(accountId: string) {
  const account = await findAccount(accountId);
  if (!account) {
    throw new CredentialOperationError("Account not found.");
  }
  const result = await runPasswordManager([
    "copy",
    "--site",
    account.site,
    "--username",
    account.username,
    "--clear-after",
    String(CLEAR_AFTER_SECONDS),
  ]);
  if (
    result.copied !== true ||
    result.password_printed !== false ||
    result.clear_after_seconds !== CLEAR_AFTER_SECONDS
  ) {
    throw new CredentialOperationError("The password manager did not confirm a secure copy.");
  }
  return { copied: true as const, clearAfterSeconds: CLEAR_AFTER_SECONDS };
}

export async function clearCredentialClipboard() {
  await clearClipboardCommand();
  return { cleared: true as const };
}
