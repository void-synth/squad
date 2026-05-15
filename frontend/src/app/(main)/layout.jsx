"use client";

import AuthGate from "@/components/auth/AuthGate.jsx";
import AppLayout from "@/components/layout/AppLayout.jsx";
import { AgentProvider } from "@/context/AgentContext.jsx";
import { DashboardProvider } from "@/context/DashboardContext.jsx";

export default function MainLayout({ children }) {
  return (
    <AuthGate>
      <DashboardProvider>
        <AgentProvider>
          <AppLayout>{children}</AppLayout>
        </AgentProvider>
      </DashboardProvider>
    </AuthGate>
  );
}
