import { Outlet } from "react-router-dom";
import { Button } from "@heroui/react";
import { useDashboard } from "../../context/DashboardContext.jsx";
import AppBottomNav from "./AppBottomNav.jsx";

/**
 * Full-width workspace + floating bottom dock (safe-area padded).
 */
export default function AppLayout() {
  const { bootstrapError, retryBootstrap } = useDashboard();

  return (
    <div className="titan-app-bg text-foreground flex min-h-dvh flex-col">
      {bootstrapError ? (
        <div className="border-danger/30 bg-danger/10 shrink-0 border-b px-4 py-3 sm:px-6">
          <div className="flex max-w-[1600px] flex-wrap items-center justify-between gap-3">
            <p className="text-danger text-sm">{bootstrapError}</p>
            <Button color="warning" variant="flat" size="sm" onPress={() => retryBootstrap()}>
              Retry
            </Button>
          </div>
        </div>
      ) : null}

      <main className="bg-content1/30 flex min-h-0 flex-1 flex-col pb-[calc(5.5rem+env(safe-area-inset-bottom))]">
        <Outlet />
      </main>

      <AppBottomNav />
    </div>
  );
}
