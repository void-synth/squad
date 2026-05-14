"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button, Card, Chip, Spinner } from "@heroui/react";
import { ArrowLeft2, Danger, WalletMoney } from "../icons/isax.jsx";
import TransactionGraph from "../components/graph/TransactionGraph.jsx";
import PageShell from "../components/layout/PageShell.jsx";
import { getTransactionDetail, formatApiError } from "../services/api.js";

const fmt = new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 });

function statusColor(status) {
  const s = (status || "").toLowerCase();
  if (s === "safe" || s === "released") return "success";
  if (s === "flagged" || s === "pending") return "warning";
  if (s === "held" || s === "escalated") return "danger";
  return "default";
}

export default function TransactionDetailPage() {
  const params = useParams();
  const rawRef = params?.ref;
  const ref = typeof rawRef === "string" ? rawRef : Array.isArray(rawRef) ? rawRef[0] : undefined;
  const router = useRouter();
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [squadBusy, setSquadBusy] = useState(false);
  const [squadRefreshNote, setSquadRefreshNote] = useState(null);

  const loadDetail = useCallback(async () => {
    if (!ref) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getTransactionDetail(ref);
      setDetail(data);
    } catch (e) {
      setError(e?.response?.status === 404 ? "Transaction not found." : formatApiError(e));
      setDetail(null);
    } finally {
      setLoading(false);
    }
  }, [ref]);

  useEffect(() => {
    if (!ref) {
      setLoading(false);
      setDetail(null);
      setError(null);
      return undefined;
    }
    void loadDetail();
    return undefined;
  }, [ref, loadDetail]);

  const refreshFromApi = useCallback(async () => {
    if (!ref) return;
    setSquadBusy(true);
    setSquadRefreshNote(null);
    try {
      const data = await getTransactionDetail(ref);
      setDetail(data);
    } catch (e) {
      setSquadRefreshNote(formatApiError(e));
    } finally {
      setSquadBusy(false);
    }
  }, [ref]);

  const tx = detail?.transaction;
  const settle = detail?.settlement;
  const fraud = detail?.fraud_alert;
  const graphData = detail?.graph_data;

  return (
    <PageShell variant="narrow" className="min-h-0">
      <Button variant="light" size="sm" className="-ml-1 mb-4 gap-2 self-start font-semibold" startContent={<ArrowLeft2 size={18} variant="Linear" />} onPress={() => router.push("/")}>
        Back to dashboard
      </Button>

      {loading ? (
        <div className="flex min-h-[200px] flex-col items-center justify-center gap-4">
          <Spinner color="primary" size="lg" />
          <p className="text-default-500 text-sm">Loading transaction…</p>
        </div>
      ) : null}

      {error ? (
        <p className="text-danger text-sm" role="alert">
          {error}
        </p>
      ) : null}

      {!loading && !error && tx ? (
        <div className="flex flex-col gap-5">
          <div>
            <h1 className="text-default-foreground text-lg font-bold uppercase tracking-wide">Transaction</h1>
            <p className="text-default-500 mt-1 text-sm">Reference and risk context</p>
          </div>

          <Card.Root className="rounded-2xl border border-default-200/80 bg-content1/90 shadow-sm">
            <Card.Header className="flex flex-wrap items-center justify-between gap-3 border-b border-default-200/60 px-5 py-4">
              <Card.Title className="text-default-foreground font-mono text-sm font-semibold">{tx.transaction_ref}</Card.Title>
              <Chip size="sm" color={statusColor(tx.status)} variant="flat" className="font-mono uppercase">
                {tx.status || "—"}
              </Chip>
            </Card.Header>
            <Card.Content className="grid gap-4 p-5 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <WalletMoney size={20} variant="Bold" className="text-primary" />
                <span className="text-default-500">Gross (Squad)</span>
                <span className="text-default-foreground text-lg font-bold">{fmt.format(tx.amount_naira ?? 0)}</span>
              </div>
              {settle ? (
                <div className="bg-content2/50 rounded-xl border border-default-200/60 px-3 py-3 text-xs leading-relaxed">
                  <p className="text-default-500 font-semibold uppercase tracking-wide">Simulated settlement</p>
                  <p className="text-default-600 mt-2">
                    Platform fee ({((Number(settle.fee_rate) || 0) * 100).toFixed(0)}%) to{" "}
                    <span className="text-default-foreground font-mono">{settle.fee_receiver_account}</span>:{" "}
                    <span className="text-default-foreground font-semibold">{fmt.format(settle.platform_fee_naira ?? 0)}</span>
                  </p>
                  <p className="text-default-600 mt-1">
                    Net after fee:{" "}
                    <span className="text-default-foreground font-semibold">{fmt.format(settle.net_settlement_naira ?? 0)}</span>
                  </p>
                </div>
              ) : null}
              <div>
                <span className="text-default-500">Risk</span>{" "}
                <span className="text-warning font-semibold">{((Number(tx.risk_score) || 0) * 100).toFixed(0)}%</span>
              </div>
              <p className="text-default-600 font-mono text-xs leading-relaxed sm:text-sm">
                {tx.sender_account} ({tx.sender_bank}) → {tx.receiver_account} ({tx.receiver_bank})
              </p>
              <p className="text-default-500 font-mono text-xs">{tx.created_at}</p>
            </Card.Content>
          </Card.Root>

          {fraud ? (
            <Card.Root className="rounded-2xl border border-danger/25 bg-danger/5">
              <Card.Header className="px-5 py-4">
                <Card.Title className="text-default-foreground flex items-center gap-2 text-sm font-semibold">
                  <Danger size={20} variant="Bold" className="text-danger" />
                  Fraud alert
                </Card.Title>
              </Card.Header>
              <Card.Content className="px-5 pb-5">
                <p className="text-default-500 text-xs font-semibold uppercase tracking-wide">
                  Level {fraud.alert_level} · {fraud.pattern_type}
                </p>
                <p className="text-default-600 mt-3 text-sm leading-relaxed">{fraud.reason}</p>
              </Card.Content>
            </Card.Root>
          ) : null}

          <Card.Root className="rounded-2xl border border-default-200/80 bg-content1/90 shadow-sm">
            <Card.Header className="flex flex-wrap items-center justify-between gap-3 border-b border-default-200/60 px-5 py-4">
              <div>
                <Card.Title className="text-default-foreground text-sm font-semibold">Squad verify</Card.Title>
                <Card.Description className="text-default-500 text-xs">
                  Live response from Squad payment verify when the server has a secret key configured.
                </Card.Description>
              </div>
              <Button size="sm" variant="bordered" isLoading={squadBusy} onPress={() => void refreshFromApi()}>
                Refresh
              </Button>
            </Card.Header>
            <Card.Content className="p-5">
              {squadRefreshNote ? (
                <p className="text-danger mb-3 text-sm" role="alert">
                  {squadRefreshNote}
                </p>
              ) : null}
              {detail?.squad != null ? (
                <pre className="text-default-600 max-h-72 overflow-auto rounded-lg bg-content2/40 p-3 font-mono text-[0.65rem] leading-relaxed whitespace-pre-wrap break-all">
                  {JSON.stringify(detail.squad, null, 2)}
                </pre>
              ) : (
                <p className="text-default-500 text-sm leading-relaxed">
                  No Squad verify payload for this reference yet. Configure <span className="font-mono">SQUAD_SECRET_KEY</span> on
                  the API server, or use a reference that exists in your Squad workspace.
                </p>
              )}
            </Card.Content>
          </Card.Root>

          <TransactionGraph graphData={graphData} />
        </div>
      ) : null}
    </PageShell>
  );
}
