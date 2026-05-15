"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { Button, Card, Input, Spinner } from "@heroui/react";
import { formatApiError, initiateSquadCheckout } from "../services/api.js";
import { useAuth } from "../context/AuthContext.jsx";

const PRESETS = [
  { label: "₦100", kobo: 10_000 },
  { label: "₦500", kobo: 50_000 },
  { label: "₦1,000", kobo: 100_000 },
  { label: "₦2,500", kobo: 250_000 },
];

export default function BillingPage() {
  const { email: authEmail } = useAuth();
  const searchParams = useSearchParams();
  const returned = searchParams.get("squad_return") === "1" || searchParams.get("status") === "success";

  const [email, setEmail] = useState(() => authEmail || "");
  const [customerName, setCustomerName] = useState("");
  const [amountKobo, setAmountKobo] = useState(PRESETS[1].kobo);
  const [customNaira, setCustomNaira] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (authEmail) {
      setEmail((prev) => (prev.trim() ? prev : authEmail));
    }
  }, [authEmail]);

  const callbackUrl = useMemo(() => {
    if (typeof window === "undefined") return "";
    return `${window.location.origin}/billing?squad_return=1`;
  }, []);

  const applyPreset = useCallback((kobo) => {
    setAmountKobo(kobo);
    setCustomNaira("");
    setError(null);
  }, []);

  const applyCustom = useCallback(() => {
    const n = parseFloat(String(customNaira).replace(/,/g, ""));
    if (Number.isNaN(n) || n <= 0) {
      setError("Enter a valid amount in Naira.");
      return;
    }
    setAmountKobo(Math.round(n * 100));
    setError(null);
  }, [customNaira]);

  const handlePay = useCallback(async () => {
    setError(null);
    const em = email.trim();
    if (!em || !em.includes("@")) {
      setError("Enter a valid email for your Squad receipt.");
      return;
    }
    setLoading(true);
    try {
      const { checkout_url: checkoutUrl } = await initiateSquadCheckout({
        email: em,
        amount_kobo: amountKobo,
        customer_name: customerName.trim() || undefined,
        callback_url: callbackUrl || undefined,
      });
      if (!checkoutUrl) {
        setError("Checkout URL missing — check Squad sandbox keys and API response.");
        setLoading(false);
        return;
      }
      window.location.assign(checkoutUrl);
    } catch (e) {
      setError(formatApiError(e));
      setLoading(false);
    }
  }, [amountKobo, callbackUrl, customerName, email]);

  const amountLabel = (amountKobo / 100).toLocaleString("en-NG", {
    style: "currency",
    currency: "NGN",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  });

  return (
    <div className="flex w-full flex-col px-3 pt-2 pb-3 sm:px-5 sm:pt-3 lg:px-6">
      <header className="mb-4 shrink-0">
        <p className="text-default-500 text-[0.65rem] font-bold uppercase tracking-[0.2em]">Support</p>
        <h1 className="text-default-foreground text-lg font-bold tracking-tight sm:text-xl">Billing</h1>
        <p className="text-default-500 mt-0.5 max-w-2xl text-sm leading-snug">
          Optional contribution via Squad&apos;s hosted checkout (sandbox or live per your backend keys). You will leave
          Titan briefly to complete payment, then return here if Squad redirects with your callback URL.
        </p>
      </header>

      {returned ? (
        <Card.Root className="border-success/30 bg-success/10 mb-4 max-w-xl rounded-2xl border">
          <Card.Content className="gap-1 px-4 py-4">
            <p className="text-success text-sm font-semibold">Thanks — payment flow returned to Titan.</p>
            <p className="text-default-600 text-xs">
              If payment succeeded, Squad emails a receipt. You can close this message and pick another amount to give
              again.
            </p>
          </Card.Content>
        </Card.Root>
      ) : null}

      <Card.Root className="border-default-200/70 max-w-xl rounded-2xl border shadow-sm">
        <Card.Content className="flex flex-col gap-4 px-5 py-5">
          <div>
            <p className="text-default-500 mb-2 text-xs font-semibold uppercase tracking-wide">Amount</p>
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((p) => (
                <Button
                  key={p.kobo}
                  size="sm"
                  variant={amountKobo === p.kobo && !customNaira ? "solid" : "bordered"}
                  color="primary"
                  className="font-semibold"
                  onPress={() => applyPreset(p.kobo)}
                >
                  {p.label}
                </Button>
              ))}
            </div>
            <p className="text-default-foreground mt-3 text-sm font-bold">{amountLabel}</p>
          </div>

          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <Input
              label="Custom (NGN)"
              placeholder="e.g. 750"
              value={customNaira}
              onValueChange={setCustomNaira}
              type="text"
              inputMode="decimal"
              className="flex-1"
            />
            <Button variant="flat" className="font-semibold sm:mb-0" onPress={applyCustom}>
              Use custom
            </Button>
          </div>

          <Input
            label="Email"
            type="email"
            value={email}
            onValueChange={setEmail}
            description="Used by Squad for receipts."
          />

          <Input
            label="Display name (optional)"
            placeholder="How we greet you on checkout"
            value={customerName}
            onValueChange={setCustomerName}
          />

          {error ? (
            <p className="text-danger text-sm font-medium" role="alert">
              {error}
            </p>
          ) : null}

          <Button
            color="primary"
            size="lg"
            className="font-bold"
            onPress={handlePay}
            isDisabled={loading}
            startContent={loading ? <Spinner size="sm" color="current" /> : null}
          >
            {loading ? "Opening Squad checkout…" : `Pay ${amountLabel} with Squad`}
          </Button>

          <p className="text-default-400 text-[0.7rem] leading-snug">
            Sandbox keys only charge test money. Production keys charge real NGN. Callback URL must be HTTPS on deploy,
            or localhost during development.
          </p>
        </Card.Content>
      </Card.Root>
    </div>
  );
}
