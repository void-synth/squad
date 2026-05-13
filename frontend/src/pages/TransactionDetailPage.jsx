import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Button, Card, Chip, Spinner } from "@heroui/react";
import { ArrowLeft2, Danger, WalletMoney } from "../icons/isax.jsx";
import TransactionGraph from "../components/graph/TransactionGraph.jsx";
import PageShell from "../components/layout/PageShell.jsx";
import { getTransactionDetail } from "../services/api.js";

const fmt = new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 });

function statusColor(status) {
  const s = (status || "").toLowerCase();
  if (s === "safe" || s === "released") return "success";
  if (s === "flagged" || s === "pending") return "warning";
  if (s === "held" || s === "escalated") return "danger";
  return "default";
}

export default function TransactionDetailPage() {
  const { ref } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    if (!ref) {
      setLoading(false);
      return undefined;
    }
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const data = await getTransactionDetail(ref);
        if (!cancelled) setDetail(data);
      } catch (e) {
        if (!cancelled) {
          setError(e?.response?.status === 404 ? "Transaction not found." : e?.message || "Failed to load");
          setDetail(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [ref]);

  const tx = detail?.transaction;
  const fraud = detail?.fraud_alert;
  const graphData = detail?.graph_data;

  return (
    <PageShell variant="narrow" className="min-h-0">
      <Button variant="light" size="sm" className="-ml-1 mb-4 gap-2 self-start font-semibold" startContent={<ArrowLeft2 size={18} variant="Linear" />} onPress={() => navigate("/")}>
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
                <span className="text-default-500">Amount</span>
                <span className="text-default-foreground text-lg font-bold">{fmt.format(tx.amount_naira ?? 0)}</span>
              </div>
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

          <TransactionGraph graphData={graphData} />
        </div>
      ) : null}
    </PageShell>
  );
}
