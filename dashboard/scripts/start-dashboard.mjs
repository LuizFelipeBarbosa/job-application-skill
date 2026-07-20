import { randomBytes } from "node:crypto";
import { spawn } from "node:child_process";

const mode = process.argv[2];
const vaultEnabled = process.argv.includes("--vault");

if (mode !== "dev" && mode !== "start") {
  console.error("Usage: node scripts/start-dashboard.mjs <dev|start> [--vault]");
  process.exit(2);
}

const environment = { ...process.env };
if (vaultEnabled) {
  const token = randomBytes(32).toString("base64url");
  environment.JOB_DASHBOARD_VAULT_TOKEN = token;
  console.log(`Account Vault URL: http://127.0.0.1:3000/#vault_token=${token}`);
} else {
  delete environment.JOB_DASHBOARD_VAULT_TOKEN;
  console.log("Account Vault disabled. Use the :vault command to enable it for one launch.");
}

const nextBinary = process.platform === "win32" ? "pnpm.cmd" : "pnpm";
const child = spawn(nextBinary, ["exec", "next", mode, "--hostname", "127.0.0.1"], {
  env: environment,
  stdio: "inherit",
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}

child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  process.exit(code ?? 1);
});
