"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Button, Card, Chip, Spinner } from "@heroui/react";
import { Danger, TickCircle } from "../icons/isax.jsx";
import {
  formatApiError,
  getHealth,
  getIntegrationQueue,
  getSquadIntegrationStatus,
  getStats,
} from "../services/api.js";

function apiBase() {
  const b = (process.env.NEXT_PUBLIC_API_URL || "").replace(/\/$/, "");
  return b || (typeof window !== "undefined" ? window.location.origin : "");
}

function SectionTitle({ title, subtitle }) {
  return (
    <div>
      <p className="text-default-foreground text-sm font-semibold">{title}</p>
      {subtitle ? <p className="text-default-500 mt-0.5 text-xs">{subtitle}</p> : null}
    </div>
  );
}

function CopyBlock({ title, subtitle, text }) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* ignore */
    }
  }, [text]);

  return (
    <Card.Root className="rounded-xl border border-default-200/80 bg-content1/60">
      <Card.Header className="flex flex-wrap items-start justify-between gap-2 border-b border-default-200/60 px-4 py-3">
        <SectionTitle title={title} subtitle={subtitle} />
        <Button size="sm" variant="flat" className="shrink-0 font-semibold" onPress={() => void copy()}>
          {copied ? "Copied" : "Copy"}
        </Button>
      </Card.Header>
      <Card.Content className="p-0">
        <pre className="text-default-600 max-h-48 overflow-auto px-4 py-3 font-mono text-[0.65rem] leading-relaxed whitespace-pre-wrap break-all">
          {text}
        </pre>
      </Card.Content>
    </Card.Root>
  );
}

function StatusChip({ ok, label }) {
  return (
    <Chip size="sm" variant="flat" color={ok ? "success" : "danger"}>
      {label}: {ok ? "yes" : "no"}
    </Chip>
  );
}

const CAPABILITY_LABELS = {
  webhook_sha512: "Webhook HMAC-SHA512",
  transaction_verify: "Payment verify",
  virtual_account_create: "Virtual account",
  payout_account_lookup: "Payout account lookup",
  payout_transfer: "Fund transfer (gated)",
  checkout_inline: "Inline checkout",
  checkout_return_probe: "Checkout return URL",
};

export default function IntegrationsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [squad, setSquad] = useState(null);
  const [health, setHealth] = useState(null);
  const [queue, setQueue] = useState(null);
  const [stats, setStats] = useState(null);

  const base = apiBase();

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [sq, h, q, st] = await Promise.all([
          getSquadIntegrationStatus(),
          getHealth(),
          getIntegrationQueue(),
          getStats(),
        ]);
        if (cancelled) return;
        setSquad(sq);
        setHealth(h);
        setQueue(q);
        setStats(st);
      } catch (e) {
        if (!cancelled) setError(formatApiError(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const examples = useMemo(() => {
    const b = base || "https://your-api.example.com";
    return [
      {
        title: "Integration status",
        subtitle: "Keys configured, sandbox base URL, capability flags",
        text: `curl -s "${b}/api/v1/integration/squad/status"`,
      },
      {
        title: "Ingest demo transactions (webhook)",
        subtitle: "From your machine — requires matching SQUAD_SECRET_KEY on API",
        text: `cd backend\npython simulate.py -n 20 -c 5 --base-url ${b}`,
      },
      {
        title: "Squad webhook URL (dashboard)",
        subtitle: "POST only — browser GET returns 405",
        text: `${b}/api/v1/webhook/squad`,
      },
      {
        title: "Verify payment",
        subtitle: "Replace TRANSACTION_REF; also on transaction detail in UI",
        text: `curl -s "${b}/api/v1/integration/squad/verify/TRANSACTION_REF"`,
      },
      {
        title: "Start checkout (Billing)",
        subtitle: "Same as Billing tab — returns checkout_url",
        text: `curl -s -X POST "${b}/api/v1/integration/squad/checkout/initiate" \\\n  -H "Content-Type: application/json" \\\n  -d '{"email":"you@example.com","amount_kobo":10000,"callback_url":"https://your-app/billing?squad_return=1"}'`,
      },
      {
        title: "Create virtual account",
        subtitle: "Sandbox VA issuance via Squad API",
        text: `curl -s -X POST "${b}/api/v1/integration/squad/virtual-account" \\\n  -H "Content-Type: application/json" \\\n  -d '{"customer_name":"Demo User","bvn":"22222222222","mobile_number":"08012345678"}'`,
      },
      {
        title: "Payout account lookup",
        subtitle: "Required before fund transfer in Squad docs",
        text: `curl -s -X POST "${b}/api/v1/integration/squad/payout/account-lookup" \\\n  -H "Content-Type: application/json" \\\n  -d '{"bank_code":"000013","account_number":"0123456789"}'`,
      },
    ];
  }, [base]);

  const docsUrl = base ? `${base}/docs` : null;

  return (
    <PageWrap>
      <header className="mb-4 shrink-0">
        <p className="text-default-500 text-[0.65rem] font-bold uppercase tracking-[0.2em]">Platform</p>
        <h1 className="text-default-foreground text-lg font-bold tracking-tight sm:text-xl">Integrations</h1>
        <p className="text-default-500 mt-0.5 max-w-2xl text-sm leading-snug">
          Squad powers webhooks (Monitoring feed), checkout (Billing), verify (transaction detail), and server-side
          proxies below. Secrets never leave the API.
        </p>
      </header>

      {loading ? (
        <div className="flex items-center gap-3 py-8">
          <Spinner color="primary" />
          <p className="text-default-400 text-sm">Loading integration status…</p>
        </div>
      ) : null}

      {error ? (
        <p className="text-danger mb-4 text-sm font-medium" role="alert">
          {error}
        </p>
      ) : null}

      {!loading && !error ? (
        <div className="flex max-w-3xl flex-col gap-5">
          <Card.Root className="rounded-2xl border border-default-200/80 bg-content1/90 shadow-sm">
            <Card.Header className="border-default-200/60 flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
              <SectionTitle title="Squad connection" subtitle="Live status from your API" />
              {docsUrl ? (
                <Button
                  as={Link}
                  href={docsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  size="sm"
                  variant="bordered"
                  className="font-semibold"
                >
                  Open API docs
                </Button>
              ) : null}
            </Card.Header>
            <Card.Content className="flex flex-col gap-4 p-5">
              <div className="flex flex-wrap gap-2">
                <StatusChip ok={squad?.secret_configured} label="Secret key" />
                <StatusChip ok={squad?.public_configured} label="Public key" />
                <Chip size="sm" variant="flat" color={squad?.payout_enabled ? "warning" : "default"}>
                  Payout: {squad?.payout_enabled ? "enabled" : "disabled (safe)"}
                </Chip>
              </div>
              <p className="text-default-500 font-mono text-xs break-all">
                API base: <span className="text-default-700">{base || "— set NEXT_PUBLIC_API_URL"}</span>
              </p>
              {squad?.base_url ? (
                <p className="text-default-500 font-mono text-xs break-all">
                  Squad: <span className="text-default-700">{squad.base_url}</span>
                </p>
              ) : null}

              <hr className="border-default-200/70" />

              <p className="text-default-500 text-xs font-semibold uppercase tracking-wide">Live signals</p>
              <ul className="text-default-600 flex flex-col gap-1.5 text-sm">
                <li>
                  Transactions in DB:{" "}
                  <strong className="text-default-foreground">{stats?.total_transactions ?? "—"}</strong>
                  {Number(stats?.total_transactions) > 0 ? (
                    <span className="text-default-400"> — Monitoring is fed by webhook ingest</span>
                  ) : (
                    <span className="text-default-400"> — run simulate.py or Squad webhooks</span>
                  )}
                </li>
                <li>
                  Queue depth: <strong className="text-default-foreground">{queue?.queue_length ?? "—"}</strong>
                  {health?.queue ? <span className="text-default-400"> ({health.queue} backend)</span> : null}
                </li>
                <li>
                  API health: <strong className="text-default-foreground">{health?.status ?? "—"}</strong>
                </li>
              </ul>

              {squad?.capabilities ? (
                <div>
                  <p className="text-default-500 mb-2 text-xs font-semibold uppercase tracking-wide">Capabilities</p>
                  <ul className="grid gap-1.5 sm:grid-cols-2">
                    {Object.entries(squad.capabilities).map(([key, on]) => (
                      <li key={key} className="flex items-center gap-2 text-sm">
                        {on ? (
                          <TickCircle size={18} variant="Bold" className="text-success shrink-0" />
                        ) : (
                          <Danger size={18} variant="Bold" className="text-default-300 shrink-0" />
                        )}
                        <span className={on ? "text-default-700" : "text-default-400"}>
                          {CAPABILITY_LABELS[key] || key}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <p className="text-default-500 text-xs font-semibold uppercase tracking-wide">In the app</p>
              <div className="flex flex-wrap gap-2">
                <Button as={Link} href="/" size="sm" variant="flat" className="font-semibold">
                  Monitoring
                </Button>
                <Button as={Link} href="/billing" size="sm" variant="flat" className="font-semibold">
                  Billing checkout
                </Button>
              </div>
            </Card.Content>
          </Card.Root>

          <section className="flex flex-col gap-3">
            <h2 className="text-default-foreground text-sm font-bold">Prove it — copy & run</h2>
            <p className="text-default-500 -mt-1 text-xs">
              Replace placeholders. Webhook simulator must use the same secret as your API host.
            </p>
            {examples.map((ex) => (
              <CopyBlock key={ex.title} title={ex.title} subtitle={ex.subtitle} text={ex.text} />
            ))}
          </section>
        </div>
      ) : null}
    </PageWrap>
  );
}

function PageWrap({ children }) {
  return (
    <div className="flex w-full flex-col px-3 pt-2 pb-6 sm:px-5 sm:pt-3 lg:px-6">{children}</div>
  );
}
