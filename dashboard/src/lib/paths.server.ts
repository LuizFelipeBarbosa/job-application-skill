import "server-only";

import path from "node:path";

export function workspaceRoot(): string {
  return process.env.JOB_DASHBOARD_WORKSPACE_ROOT
    ? path.resolve(/* turbopackIgnore: true */ process.env.JOB_DASHBOARD_WORKSPACE_ROOT)
    : path.resolve(/* turbopackIgnore: true */ process.cwd(), "..");
}

function configuredPath(environmentKey: string, fallback: string): string {
  const configured = process.env[environmentKey];
  return configured
    ? path.resolve(/* turbopackIgnore: true */ configured)
    : path.join(/* turbopackIgnore: true */ workspaceRoot(), fallback);
}

export function trackerStatePath(): string {
  return configuredPath("JOB_DASHBOARD_TRACKER_PATH", "private/application-state.json");
}

export function successfulApplicationsPath(): string {
  return configuredPath(
    "JOB_DASHBOARD_SUCCESSFUL_PATH",
    "private/successful-applications.json",
  );
}

export function outcomesPath(): string {
  return configuredPath("JOB_DASHBOARD_OUTCOMES_PATH", "private/application-outcomes.json");
}

export function accountsPath(): string {
  return configuredPath("JOB_DASHBOARD_ACCOUNTS_PATH", "private/accounts.json");
}

export function passwordManagerPath(): string {
  return configuredPath(
    "JOB_DASHBOARD_PASSWORD_MANAGER_PATH",
    ".agents/skills/apply-to-jobs/scripts/password_manager.py",
  );
}

export function dashboardTimezone(): string {
  return process.env.JOB_DASHBOARD_TIMEZONE || "America/Los_Angeles";
}
