import { mkdtemp, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const execFilePromiseMock = vi.hoisted(() => vi.fn());

vi.mock("node:child_process", async (importOriginal) => {
  const actual = await importOriginal<typeof import("node:child_process")>();
  const execFileMock = vi.fn();
  Object.defineProperty(execFileMock, Symbol.for("nodejs.util.promisify.custom"), {
    value: execFilePromiseMock,
  });
  return {
    ...actual,
    default: { ...actual, execFile: execFileMock },
    execFile: execFileMock,
  };
});

import {
  copyAccountPassword,
  CredentialOperationError,
  listAccountSummaries,
} from "@/lib/accounts.server";

const originalEnvironment = { ...process.env };

describe("account vault bridge", () => {
  beforeEach(async () => {
    execFilePromiseMock.mockReset();
    const directory = await mkdtemp(path.join(os.tmpdir(), "job-accounts-"));
    const metadataPath = path.join(directory, "accounts.json");
    await writeFile(
      metadataPath,
      JSON.stringify({
        schema_version: 1,
        accounts: [
          {
            site: "careers.example.com",
            username: "candidate@example.com",
            created_at: "2026-07-14T17:00:00+00:00",
            updated_at: "2026-07-15T17:00:00+00:00",
            permission_confirmed_at: "2026-07-14T17:00:00+00:00",
          },
        ],
      }),
      "utf8",
    );
    process.env.JOB_DASHBOARD_ACCOUNTS_PATH = metadataPath;
    process.env.JOB_DASHBOARD_PASSWORD_MANAGER_PATH = path.join(directory, "password-manager.py");
    process.env.JOB_DASHBOARD_WORKSPACE_ROOT = directory;
  });

  afterEach(() => {
    process.env = { ...originalEnvironment };
  });

  it("resolves an opaque account id and copies through an argument array without a shell", async () => {
    execFilePromiseMock.mockResolvedValue({
      stdout: JSON.stringify({
        copied: true,
        site: "careers.example.com",
        username: "candidate@example.com",
        password_printed: false,
        clear_after_seconds: 30,
      }),
      stderr: "",
    });
    const [account] = await listAccountSummaries();
    expect(account).toMatchObject({
      site: "careers.example.com",
      username: "candidate@example.com",
      loginUrl: "https://careers.example.com/",
    });
    expect(account.id).not.toContain(account.site);

    await expect(copyAccountPassword(account.id)).resolves.toEqual({
      copied: true,
      clearAfterSeconds: 30,
    });
    const [, argumentsList, options] = execFilePromiseMock.mock.calls.at(-1)!;
    expect(argumentsList).toEqual([
      process.env.JOB_DASHBOARD_PASSWORD_MANAGER_PATH,
      "--metadata",
      process.env.JOB_DASHBOARD_ACCOUNTS_PATH,
      "copy",
      "--site",
      "careers.example.com",
      "--username",
      "candidate@example.com",
      "--clear-after",
      "30",
    ]);
    expect(options.shell).toBeUndefined();
    expect(JSON.stringify(argumentsList)).not.toContain("secret-value");
  });

  it("refuses arbitrary identifiers and unsafe helper output", async () => {
    await expect(copyAccountPassword("arbitrary-account")).rejects.toThrow("Account not found");

    const [account] = await listAccountSummaries();
    execFilePromiseMock.mockResolvedValue({
      stdout: JSON.stringify({ copied: true, password: "secret-value" }),
      stderr: "",
    });
    await expect(copyAccountPassword(account.id)).rejects.toEqual(
      expect.any(CredentialOperationError),
    );
  });
});
