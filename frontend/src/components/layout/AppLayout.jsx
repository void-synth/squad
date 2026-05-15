"use client";

import { Button } from "@heroui/react";
import { useDashboard } from "../../context/DashboardContext.jsx";
import AppSidebar from "./AppSidebar.jsx";

/**
 * Left sidebar + main workspace (Next.js App Router).
 */
export default function AppLayout({ children }) {
  const { bootstrapError, retryBootstrap } = useDashboard();

  return (
    <div className="titan-app-bg text-foreground flex h-dvh min-h-0 max-h-dvh flex-row overflow-hidden">
      <AppSidebar />

      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
        {bootstrapError ? (
          <div className="border-danger/30 bg-danger/10 shrink-0 border-b px-4 py-3 sm:px-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-danger text-sm">{bootstrapError}</p>
              <Button color="warning" variant="flat" size="sm" onPress={() => retryBootstrap()}>
                Retry
              </Button>
            </div>
          </div>
        ) : null}

        <main className="bg-content1/30 flex min-h-0 min-w-0 w-full flex-1 flex-col overflow-y-auto overflow-x-hidden overscroll-y-contain [-webkit-overflow-scrolling:touch]">
          {/* Single scroll region for the workspace (fixes mobile / nested flex scroll traps). */}
          <div className="mx-auto flex w-full min-w-0 max-w-[1360px] flex-col pb-6">{children}</div>
        </main>
      </div>
    </div>
  );
}
