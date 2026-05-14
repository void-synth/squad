"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@heroui/react";
import { Home2, Notification } from "../../icons/isax.jsx";
import { useAuth } from "../../context/AuthContext.jsx";

function navClass(isActive) {
  return [
    "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold no-underline transition-colors",
    isActive
      ? "bg-primary/15 text-primary border border-primary/25"
      : "text-default-600 hover:bg-default-100 hover:text-default-foreground border border-transparent",
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

  return (
    <aside className="border-default-200/80 bg-content1/95 sticky top-0 z-40 flex h-dvh w-56 shrink-0 flex-col border-r backdrop-blur-md">
      <div className="flex h-16 items-center gap-3 border-b border-default-200/70 px-4">
        <span className="bg-primary/15 ring-primary/20 relative flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-xl ring-1">
          <Image src="/titan-logo.png" alt="Titan" width={40} height={40} className="object-contain p-1" priority />
        </span>
        <div className="min-w-0">
          <Link href="/" className="text-default-foreground block truncate text-sm font-bold uppercase tracking-[0.15em]">
            Titan
          </Link>
          <p className="text-default-500 truncate text-[0.65rem] font-medium">Fraud ops</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-3" aria-label="Primary">
        <Link href="/" className={navClass(isHome)}>
          <Home2 size={20} variant={isHome ? "Bold" : "Linear"} className="shrink-0" />
          Monitoring
        </Link>
        <Link href="/alerts" className={navClass(isAlerts && !isHome)}>
          <Notification size={20} variant={isAlerts && !isHome ? "Bold" : "Linear"} className="shrink-0" />
          Alerts
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
