import { DashboardApp } from "@/components/dashboard-app";
import { buildDashboardSnapshot } from "@/lib/data.server";

export const dynamic = "force-dynamic";

async function loadInitialData() {
  try {
    return { data: await buildDashboardSnapshot(), error: null };
  } catch (error) {
    return {
      data: null,
      error: error instanceof Error ? error.message : "The dashboard could not be loaded.",
    };
  }
}

export default async function HomePage() {
  const result = await loadInitialData();
  if (result.data) {
    return <DashboardApp initialData={result.data} />;
  }

  return (
      <main className="fatal-shell">
        <section className="fatal-card">
          <span className="eyebrow">Local data unavailable</span>
          <h1>The command center needs its tracker.</h1>
          <p>{result.error}</p>
          <p className="fatal-hint">
            Start the dashboard from the repository and confirm that the private tracker files exist.
          </p>
        </section>
      </main>
  );
}
