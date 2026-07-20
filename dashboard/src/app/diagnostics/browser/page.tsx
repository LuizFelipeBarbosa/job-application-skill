"use client";

import { useState } from "react";

export default function BrowserDiagnosticPage() {
  const [name, setName] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [fileName, setFileName] = useState("");
  const [submitted, setSubmitted] = useState(false);

  return (
    <main style={{ margin: "4rem auto", maxWidth: 720, padding: "0 1.5rem", fontFamily: "sans-serif" }}>
      <p>LOCAL DIAGNOSTIC / NO CANDIDATE DATA</p>
      <h1>Chrome and Computer Use fixture</h1>
      <p>
        Use only synthetic values. This local page verifies navigation, form entry, upload,
        screenshot inspection, and confirmation-state reading without contacting a job site.
      </p>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          setSubmitted(Boolean(name && confirmed && fileName));
        }}
      >
        <label style={{ display: "grid", gap: 8, marginTop: 24 }}>
          Synthetic applicant name
          <input
            aria-label="Synthetic applicant name"
            onChange={(event) => setName(event.target.value)}
            required
            value={name}
          />
        </label>
        <label style={{ display: "grid", gap: 8, marginTop: 24 }}>
          Synthetic file
          <input
            accept="text/plain"
            aria-label="Synthetic file"
            onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "")}
            required
            type="file"
          />
        </label>
        <label style={{ display: "flex", gap: 8, marginTop: 24 }}>
          <input
            checked={confirmed}
            onChange={(event) => setConfirmed(event.target.checked)}
            type="checkbox"
          />
          I confirm these values are synthetic.
        </label>
        <button style={{ marginTop: 24 }} type="submit">Complete diagnostic</button>
      </form>
      <output aria-live="polite" style={{ display: "block", marginTop: 32 }}>
        {submitted
          ? `DIAGNOSTIC PASSED: ${name}; ${fileName}; confirmation checked.`
          : "DIAGNOSTIC PENDING"}
      </output>
    </main>
  );
}
