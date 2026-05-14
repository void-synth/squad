"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Spinner } from "@heroui/react";
import { useAuth } from "@/context/AuthContext.jsx";

export default function AuthGate({ children }) {
  const { mounted, isAuthenticated } = useAuth();
  const router = useRouter();
  const pathname = usePathname() ?? "/";

  useEffect(() => {
    if (!mounted) return;
    if (isAuthenticated) return;
    const from = encodeURIComponent(pathname);
    router.replace(`/login?from=${from}`);
  }, [mounted, isAuthenticated, router, pathname]);

  if (!mounted || !isAuthenticated) {
    return (
      <div className="titan-app-bg flex min-h-dvh flex-col items-center justify-center gap-3 text-default-500">
        <Spinner color="primary" size="lg" />
        <p className="text-sm font-medium">Checking session…</p>
      </div>
    );
  }

  return children;
}
