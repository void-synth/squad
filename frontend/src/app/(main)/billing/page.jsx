import { Suspense } from "react";
import BillingPage from "@/views/BillingPage.jsx";
import { Spinner } from "@heroui/react";

function BillingFallback() {
  return (
    <div className="flex w-full flex-col items-center justify-center gap-3 px-6 py-16">
      <Spinner color="primary" />
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
