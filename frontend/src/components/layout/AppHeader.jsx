"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Badge } from "@heroui/react";
import { Home2, Notification, SecuritySafe } from "../../icons/isax.jsx";
import { useDashboard } from "../../context/DashboardContext.jsx";

function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <span className="text-default-500 hidden text-sm font-medium tabular-nums sm:inline">
      {now.toLocaleString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: false,
      })}
    </span>
  );
}

function navClass(isActive) {
  return [
    "inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold transition-colors",
    isActive
      ? "bg-primary/15 text-primary border-primary/30 border"
      : "text-default-600 hover:text-default-foreground border border-transparent hover:bg-default-100",
  ].join(" ");
}

export default function AppHeader() {
  const { isConnected } = useDashboard();
  const pathname = usePathname() ?? "";
  const isDashboard = pathname === "/";
  const isAlerts = pathname.startsWith("/alerts");

  return (
    <header className="border-default-200/70 bg-content1/90 sticky top-0 z-50 shrink-0 border-b backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-[1600px] items-center justify-between gap-3 px-4 sm:h-16 sm:gap-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-3 sm:gap-4">
          <div className="flex items-center gap-2.5">
            <span
              className={`inline-flex h-2 w-2 shrink-0 rounded-full sm:h-2.5 sm:w-2.5 ${isConnected ? "bg-success shadow-[0_0_10px_hsl(var(--heroui-success)/0.45)]" : "bg-default-400"}`}
              aria-hidden
            />
            <Link href="/" className="group flex min-w-0 items-center gap-2 no-underline">
              <SecuritySafe size={22} variant="Bold" className="text-primary shrink-0" />
              <span className="text-primary truncate text-sm font-bold uppercase tracking-[0.18em] sm:text-base">Titan</span>
            </Link>
          </div>

          <nav className="bg-default-100/80 flex items-center gap-0.5 rounded-xl p-0.5 sm:gap-1" aria-label="Primary">
            <Link href="/" aria-label="Dashboard" className={navClass(isDashboard)}>
              <Home2 size={17} variant="Linear" className="shrink-0" />
              <span className="hidden sm:inline">Dashboard</span>
            </Link>
            <Link href="/alerts" aria-label="Alerts inbox" className={navClass(isAlerts)}>
              <Notification size={17} variant="Linear" className="shrink-0" />
              <span className="hidden sm:inline">Alerts</span>
            </Link>
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <Clock />
          <Badge size="sm" variant="flat" color={isConnected ? "success" : "danger"} className="uppercase tracking-wide">
            {isConnected ? "Live" : "Off"}
          </Badge>
        </div>
      </div>
    </header>
  );
}
