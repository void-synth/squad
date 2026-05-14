"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button, Card, Chip, Spinner } from "@heroui/react";
import { ArrowRight2 } from "../icons/isax.jsx";
import PageShell from "../components/layout/PageShell.jsx";
import { formatApiError, getAlerts } from "../services/api.js";
import { normalizeAlert } from "../utils/alertNormalize.js";

const fmt = new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 });

export default function AlertsInboxPage() {
  const router = useRouter();
  const [mode, setMode] = useState("open");
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = mode === "open" ? { resolved: false } : {};
      const data = await getAlerts(params);
      setRows(Array.isArray(data) ? data.map((a) => normalizeAlert(a)).filter(Boolean) : []);
    } catch (e) {
      setError(formatApiError(e));
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <PageShell variant="default" title="Alerts inbox" description="Full case list — open any row to see the transfer and graph." className="min-h-0">
      <div className="mb-6 flex flex-wrap gap-2">
        <Button size="sm" radius="lg" variant={mode === "open" ? "solid" : "bordered"} color={mode === "open" ? "primary" : "default"} onPress={() => setMode("open")}>
          Open only
        </Button>
        <Button size="sm" radius="lg" variant={mode === "all" ? "solid" : "bordered"} color={mode === "all" ? "primary" : "default"} onPress={() => setMode("all")}>
          All alerts
        </Button>
      </div>

      {loading ? (
        <div className="text-default-500 flex items-center gap-3 py-8">
          <Spinner size="md" color="primary" />
          Loading…
        </div>
      ) : null}

      {error ? (
        <p className="text-danger py-2 text-sm" role="alert">
          {error}
        </p>
      ) : null}

      <ul className="m-0 flex list-none flex-col gap-3 p-0">
        {rows.map((a) => {
          const resolved = Boolean(a.resolved_at);
          const ref = a.transaction_ref || a.transaction?.transaction_ref;
          return (
            <li key={a.id}>
              <Card.Root className={`rounded-2xl border border-default-200/80 ${resolved ? "bg-content2/40 opacity-90" : "bg-content1"} shadow-sm`}>
                <Card.Content className="gap-3 p-4">
                  <div className="flex flex-wrap justify-between gap-3">
                    <div>
                      <p className="text-default-foreground font-mono text-sm font-bold">
                        L{a.alert_level} · {(Number(a.risk_score || 0) * 100).toFixed(0)}%
                      </p>
                      <p className="text-default-500 mt-1 text-xs">{a.pattern_type}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-default-foreground text-sm font-semibold">{fmt.format(a.amount_naira ?? a.transaction?.amount_naira ?? 0)}</p>
                      <Chip size="sm" variant="flat" color={resolved ? "success" : "warning"} className="mt-2 uppercase">
                        {(a.action_taken || "").toUpperCase()}
                        {resolved ? ` · ${a.resolved_at}` : ""}
                      </Chip>
                    </div>
                  </div>
                  {ref ? (
                    <Button
                      variant="bordered"
                      size="sm"
                      className="w-full font-semibold"
                      endContent={<ArrowRight2 size={16} variant="Linear" />}
                      onPress={() => router.push(`/transactions/${encodeURIComponent(ref)}`)}
                    >
                      View transaction
                    </Button>
                  ) : null}
                </Card.Content>
              </Card.Root>
            </li>
          );
        })}
      </ul>

      {!loading && rows.length === 0 ? <p className="text-default-500 py-8 text-sm">No alerts in this view.</p> : null}
    </PageShell>
  );
}
