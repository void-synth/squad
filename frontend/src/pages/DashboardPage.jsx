import { useEffect, useState } from "react";
import { Spinner } from "@heroui/react";
import AnalyticsPanel from "../components/dashboard/AnalyticsPanel.jsx";
import TransactionFeed from "../components/dashboard/TransactionFeed.jsx";
import AlertPanel from "../components/alerts/AlertPanel.jsx";
import { useDashboard } from "../context/DashboardContext.jsx";

/**
 * Layout aligned with common TM / fraud dashboards (e.g. Retool fraud templates, Forest “monitoring” workspaces):
 * — KPI + trend band across the top
 * — Primary “collection” = transaction table (widest column)
 * — Right “investigation” rail = active alert / case actions
 */
export default function DashboardPage() {
  const { isConnected } = useDashboard();
  const [latched, setLatched] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setLatched(true), 2200);
    return () => clearTimeout(t);
  }, []);

  const ready = isConnected || latched;

  if (!ready) {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-4 px-6 py-16 text-default-500">
        <Spinner color="primary" size="lg" />
        <p className="text-default-400 text-sm font-medium">Connecting to Titan…</p>
      </div>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col px-3 py-3 sm:px-5 sm:py-4 lg:px-6 lg:py-5">
      <header className="mb-4 shrink-0 lg:mb-5">
        <p className="text-default-500 text-[0.65rem] font-bold uppercase tracking-[0.2em]">Workspace</p>
        <h1 className="text-default-foreground text-lg font-bold tracking-tight sm:text-xl">Transaction monitoring</h1>
        <p className="text-default-500 mt-1 max-w-3xl text-sm leading-relaxed">
          Review live transfers, open cases from the queue, and act on holds — same flow as typical fraud and case tools.
        </p>
      </header>

      {/* Metrics + throughput band (full width) */}
      <section className="mb-4 shrink-0 lg:mb-5">
        <AnalyticsPanel layout="workspace" />
      </section>

      {/* Primary table | Case inspector (matches “collection + side panel” pattern) */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
        <section className="flex min-h-0 flex-col" aria-label="Transactions">
          <TransactionFeed />
        </section>
        <section className="flex min-h-0 flex-col" aria-label="Case actions">
          <AlertPanel />
        </section>
      </div>
    </div>
  );
}
