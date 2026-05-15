import { Suspense } from "react";
import BillingPage from "@/views/BillingPage.jsx";

/** Server-safe fallback — do not import @heroui here (breaks Next Server Components build). */
function BillingFallback() {
  return (
    <div className="flex w-full flex-col items-center justify-center gap-3 px-6 py-16">
      <div
        className="border-primary h-8 w-8 animate-spin rounded-full border-2 border-t-transparent"
        aria-hidden
      />
      <p className="text-default-400 text-sm">Loading billing…</p>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<BillingFallback />}>
      <BillingPage />
    </Suspense>
  );
}
