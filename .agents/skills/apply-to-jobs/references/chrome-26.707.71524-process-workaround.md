# Chrome 26.707.71524 protected-process workaround

Use this recovery only when normal Chrome initialization fails with exactly:

```text
Cannot redefine property: process
```

This is a session-only compatibility workaround for the OpenAI-bundled Chrome plugin version `26.707.71524`. Do not apply it preemptively, for another error, or to any other version. Prefer an updated plugin when one is available.

## Guard conditions

Proceed only when all conditions are true:

1. Resolve the active installed Chrome plugin root from the loaded Chrome skill or plugin cache. Do not edit a marketplace source or guess the active versioned path.
2. Read `.codex-plugin/plugin.json` from that root and verify `name` is `chrome` and `version` is exactly `26.707.71524`.
3. Verify `scripts/browser-client.mjs` contains the following block exactly once:

   ```js
   globalThis.process = processShim;
   globalThis.global = globalThis.global ?? globalThis;
   globalThis.global.process = processShim;
   ```

4. Confirm the observed bootstrap error is exactly `Cannot redefine property: process`.

If any condition fails, leave the plugin untouched and use normal Chrome troubleshooting or request an updated plugin.

## Apply only long enough to initialize the session

1. Record the original file's SHA-256 digest so restoration can be verified.
2. Use `apply_patch` to replace only the guarded three-line block with:

   ```js
   const process = processShim;
   const global = Object.create(globalThis);
   Object.defineProperty(global, "process", { value: processShim });
   ```

3. Make no other plugin changes. In the same task, immediately load the patched `browser-client.mjs` and initialize the Chrome browser controls. If the failed module import is cached, use a fresh JavaScript runtime for this initialization.
4. As soon as browser-client setup succeeds or fails, use `apply_patch` to restore the exact original three-line block before navigating to any website or doing other work.
5. Verify the restored file's SHA-256 digest matches the value recorded before the patch. If it does not, stop and restore the original file before continuing.
6. Continue using the already-loaded in-memory browser client for the current session. Do not re-import it after restoration unless a fresh runtime is required; a fresh runtime may reproduce the incompatibility.

If a prior interrupted attempt left the replacement block in the cached file, restore the original block first. Never leave this workaround installed between sessions, alter the Chrome extension or native host, or treat the workaround as a permanent plugin fix.
