"use client";

import { useEffect, useMemo, useState } from "react";

import { ArrowUpRightIcon, CopyIcon, LockIcon, SearchIcon } from "@/components/icons";
import { formatDate } from "@/lib/format";
import type { AccountsPayload } from "@/lib/types";
import styles from "./dashboard.module.css";

type AccountVaultProps = {
  timeZone: string;
};

export function AccountVault({ timeZone }: AccountVaultProps) {
  const [payload, setPayload] = useState<AccountsPayload | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [activeAccountId, setActiveAccountId] = useState<string | null>(null);
  const [clearCountdown, setClearCountdown] = useState(0);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/accounts", { cache: "no-store" });
      const result = (await response.json()) as AccountsPayload & { error?: string };
      if (!response.ok) throw new Error(result.error || "Account Vault could not be loaded.");
      setPayload(result);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Account Vault could not be loaded.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!clearCountdown) return;
    const timer = window.setInterval(() => {
      setClearCountdown((value) => {
        if (value <= 1) {
          window.clearInterval(timer);
          setNotice("Clipboard clear requested automatically.");
          setActiveAccountId(null);
          return 0;
        }
        return value - 1;
      });
    }, 1_000);
    return () => window.clearInterval(timer);
  }, [clearCountdown]);

  const accounts = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    if (!normalizedSearch) return payload?.accounts ?? [];
    return (payload?.accounts ?? []).filter((account) =>
      `${account.site} ${account.username}`.toLowerCase().includes(normalizedSearch),
    );
  }, [payload, search]);

  const securePost = async (url: string) => {
    if (!payload?.csrfToken) throw new Error("Reload Account Vault to refresh its security session.");
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Job-Dashboard-CSRF": payload.csrfToken,
      },
      body: "{}",
    });
    const result = (await response.json()) as { error?: string; copied?: boolean; clearAfterSeconds?: number };
    if (!response.ok) throw new Error(result.error || "The credential action failed.");
    return result;
  };

  const copyPassword = async (accountId: string) => {
    setError("");
    setNotice("");
    setActiveAccountId(accountId);
    try {
      const result = await securePost(`/api/accounts/${encodeURIComponent(accountId)}/copy-password`);
      setClearCountdown(result.clearAfterSeconds ?? 30);
      setNotice("Password copied from the OS vault. Paste it now.");
    } catch (copyError) {
      setActiveAccountId(null);
      setError(copyError instanceof Error ? copyError.message : "The password could not be copied.");
    }
  };

  const clearNow = async () => {
    setError("");
    try {
      await securePost("/api/clipboard/clear");
      setClearCountdown(0);
      setActiveAccountId(null);
      setNotice("Clipboard cleared.");
    } catch (clearError) {
      setError(clearError instanceof Error ? clearError.message : "The clipboard could not be cleared.");
    }
  };

  const copyUsername = async (username: string) => {
    try {
      await navigator.clipboard.writeText(username);
      setNotice("Username copied.");
    } catch {
      setError("The browser could not copy the username.");
    }
  };

  return (
    <section className={styles.vaultWorkspace}>
      <header className={styles.vaultHero}>
        <div className={styles.vaultSeal}>
          <LockIcon />
          <span>Local only</span>
        </div>
        <div>
          <span className={styles.eyebrow}>OS credential bridge</span>
          <h2>Account Vault</h2>
          <p>
            Passwords move from Keychain to your system clipboard. They are never displayed,
            returned to the browser, or stored by this dashboard.
          </p>
        </div>
        <div className={styles.vaultStatus} data-available={payload?.vaultAvailable || false}>
          <span />
          {loading ? "Checking secure vault…" : payload?.vaultMessage || "Vault unavailable"}
        </div>
      </header>

      <aside className={styles.clipboardWarning}>
        <strong>Clipboard safety</strong>
        <p>
          Copied passwords clear automatically after 30 seconds. Clipboard-history software may
          retain copied values, so disable it when handling credentials.
        </p>
        {clearCountdown ? (
          <button className={styles.warningAction} onClick={() => void clearNow()} type="button">
            Clear now · {clearCountdown}s
          </button>
        ) : null}
      </aside>

      <div className={styles.vaultToolbar}>
        <div className={styles.searchField}>
          <SearchIcon />
          <input
            aria-label="Search account vault"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search site or username…"
            type="search"
            value={search}
          />
        </div>
        <button className={styles.secondaryButton} disabled={loading} onClick={() => void load()} type="button">
          Refresh accounts
        </button>
      </div>

      {error ? <p className={styles.vaultError}>{error}</p> : null}
      {notice ? <p className={styles.vaultNotice} role="status">{notice}</p> : null}

      {loading ? (
        <div className={styles.vaultLoading}>Reading non-secret account metadata…</div>
      ) : accounts.length ? (
        <div className={styles.accountGrid}>
          {accounts.map((account, index) => (
            <article className={styles.accountCard} key={account.id} style={{ "--reveal-index": index } as React.CSSProperties}>
              <header>
                <span className={styles.accountIndex}>{String(index + 1).padStart(2, "0")}</span>
                <div>
                  <h3>{account.site}</h3>
                  <p>{account.username}</p>
                </div>
              </header>
              <dl>
                <div>
                  <dt>Created</dt>
                  <dd>{formatDate(account.createdAt, timeZone)}</dd>
                </div>
                <div>
                  <dt>Updated</dt>
                  <dd>{formatDate(account.updatedAt, timeZone)}</dd>
                </div>
              </dl>
              <footer>
                {account.loginUrl ? (
                  <a href={account.loginUrl} rel="noreferrer" target="_blank">
                    Open login <ArrowUpRightIcon />
                  </a>
                ) : (
                  <span className={styles.muted}>No safe login URL</span>
                )}
                <button onClick={() => void copyUsername(account.username)} type="button">
                  <CopyIcon /> Username
                </button>
                <button
                  className={styles.copyPasswordButton}
                  disabled={!payload?.vaultAvailable || Boolean(activeAccountId)}
                  onClick={() => void copyPassword(account.id)}
                  type="button"
                >
                  <LockIcon />
                  {activeAccountId === account.id
                    ? clearCountdown
                      ? `Copied · ${clearCountdown}s`
                      : "Copying…"
                    : "Copy password"}
                </button>
              </footer>
            </article>
          ))}
        </div>
      ) : (
        <div className={styles.emptyVault}>
          <LockIcon />
          <h3>No matching application accounts</h3>
          <p>Accounts appear here after the existing password manager records them.</p>
        </div>
      )}
    </section>
  );
}
