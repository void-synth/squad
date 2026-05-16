"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@heroui/react";
import { Chart2, Home2, Notification, SecuritySafe, WalletMoney } from "../../icons/isax.jsx";
import { useAuth } from "../../context/AuthContext.jsx";

function navClass(isActive) {
  return [
    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold no-underline transition-colors",
    isActive
      ? "bg-primary/15 text-primary border border-primary/25"
      : "text-default-600 hover:bg-default-100/80 hover:text-default-foreground border border-transparent",
  ].join(" ");
}

/**
 * Left rail navigation (Next.js App Router).
 */
export default function AppSidebar() {
  const pathname = usePathname() ?? "";
  const router = useRouter();
  const { email, logout } = useAuth();
  const isHome = pathname === "/";
  const isAlerts = pathname === "/alerts" || pathname.startsWith("/alerts/");
  const isAgent = pathname === "/agent" || pathname.startsWith("/agent/");
  const isBilling = pathname === "/billing" || pathname.startsWith("/billing/");
  const isIntegrations = pathname === "/integrations" || pathname.startsWith("/integrations/");

  return (
    <aside className="titan-sidebar-float sticky top-3 z-40 my-3 ml-3 flex h-[calc(100dvh-1.5rem)] w-64 min-h-0 shrink-0 flex-col overflow-hidden">
      <div className="border-default-200/70 flex h-16 shrink-0 items-center gap-3 border-b px-4">
        <span className="bg-primary/15 relative flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-xl">
          <Image src="/titan-logo.png" alt="Titan" width={40} height={40} className="object-contain p-1" priority />
        </span>
        <div className="min-w-0">
          <Link href="/" className="text-default-foreground block truncate text-sm font-bold uppercase tracking-[0.15em]">
            Titan
          </Link>
          <p className="text-default-500 truncate text-[0.65rem] font-medium">Fraud ops</p>
        </div>
      </div>

      <nav className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-3" aria-label="Primary">
        <Link href="/" className={navClass(isHome)}>
          <Home2 size={20} variant={isHome ? "Bold" : "Linear"} className="shrink-0" />
          Monitoring
        </Link>
        <Link
          href="/alerts"
          className={navClass(isAlerts && !isHome && !isAgent && !isBilling && !isIntegrations)}
        >
          <Notification
            size={20}
            variant={isAlerts && !isHome && !isAgent && !isBilling && !isIntegrations ? "Bold" : "Linear"}
            className="shrink-0"
          />
          Alerts
        </Link>
        <Link href="/agent" className={navClass(isAgent)}>
          <SecuritySafe size={20} variant={isAgent ? "Bold" : "Linear"} className="shrink-0" />
          Agent
        </Link>
        <Link href="/billing" className={navClass(isBilling)}>
          <WalletMoney size={20} variant={isBilling ? "Bold" : "Linear"} className="shrink-0" />
          Billing
        </Link>
        <Link href="/integrations" className={navClass(isIntegrations)}>
          <Chart2 size={20} variant={isIntegrations ? "Bold" : "Linear"} className="shrink-0" />
          Integrations
        </Link>
      </nav>

      <div className="border-default-200/70 shrink-0 border-t p-3">
        <p className="text-default-400 mb-2 truncate px-1 text-xs font-medium" title={email || ""}>
          {email || "Signed in"}
        </p>
        <Button
          size="sm"
          variant="bordered"
          className="w-full font-semibold"
          onPress={() => {
            logout();
            router.replace("/login");
          }}
        >
          Sign out
        </Button>
      </div>
    </aside>
  );
}
