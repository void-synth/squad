import { useEffect, useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import { Button, Card, Chip, Spinner } from "@heroui/react";
import { ArrowRight2, Flash, Radar2 } from "../../icons/isax.jsx";
import { useDashboard } from "../../context/DashboardContext.jsx";

const fmt = new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 });

const STATUS_CHIPS = [
  { value: null, label: "All" },
  { value: "pending", label: "Pending" },
  { value: "safe", label: "Safe" },
  { value: "flagged", label: "Flagged" },
  { value: "held", label: "Held" },
  { value: "released", label: "Released" },
  { value: "escalated", label: "Escalated" },
];

function timeAgo(iso) {
  if (!iso) return "";
  const t = new Date(iso).getTime();
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000));
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  return `${h}h ago`;
}

function statusChipColor(status) {
  const s = (status || "").toLowerCase();
  if (s === "safe" || s === "released") return "success";
  if (s === "flagged" || s === "pending") return "warning";
  if (s === "held" || s === "escalated") return "danger";
  return "default";
}

export default function TransactionFeed() {
  const {
    transactions,
    isConnected,
    transactionStatusFilter,
    setTransactionStatusFilter,
    transactionsLoading,
  } = useDashboard();
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [transactions.length, transactionStatusFilter]);

  const count = transactions.length;
  const rows = useMemo(() => transactions, [transactions]);

  return (
    <Card.Root className="flex min-h-0 flex-1 flex-col rounded-2xl border border-default-200/80 bg-content1/80 shadow-sm backdrop-blur-sm">
      <Card.Header className="flex flex-col gap-3 border-b border-default-200/60 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Card.Title className="text-default-foreground text-sm font-semibold">Live feed</Card.Title>
          <Card.Description className="text-default-500 text-xs">Inbound transfers · newest first</Card.Description>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-default-500 text-xs tabular-nums">
            {count.toLocaleString()} <span className="text-default-600">rows</span>
          </span>
          <div className="flex items-center gap-2">
            <Flash size={16} variant={isConnected ? "Bold" : "Linear"} className={isConnected ? "text-success" : "text-default-500"} />
            <span className="text-default-500 text-[0.65rem] font-bold uppercase tracking-wider">{isConnected ? "Live" : "Idle"}</span>
          </div>
        </div>
      </Card.Header>

      <div className="flex flex-wrap gap-2 border-b border-default-200/60 px-4 py-3">
        {STATUS_CHIPS.map((c) => {
          const active = transactionStatusFilter === c.value;
          return (
            <Button
              key={c.label}
              size="sm"
              radius="lg"
              variant={active ? "solid" : "bordered"}
              color={active ? "primary" : "default"}
              className="min-w-0 font-semibold uppercase tracking-wide"
              onPress={() => setTransactionStatusFilter(c.value)}
            >
              {c.label}
            </Button>
          );
        })}
      </div>

      <Card.Content className="relative min-h-0 flex-1 overflow-hidden p-0">
        {transactionsLoading ? (
          <div className="bg-content1/60 absolute inset-0 z-[1] flex items-center justify-center gap-3 backdrop-blur-sm">
            <Spinner color="primary" size="md" />
            <span className="text-default-500 text-sm">Loading…</span>
          </div>
        ) : null}
        <div ref={listRef} className="min-h-0 flex-1 overflow-y-auto overscroll-contain p-2 sm:p-3">
        <div className="flex flex-col gap-2">
          {rows.map((tx) => {
            const ref = tx.transaction_ref || tx.id;
            const to = `/transactions/${encodeURIComponent(String(ref))}`;
            return (
              <Link
                key={String(ref)}
                to={to}
                className="group border border-default-200/60 bg-content2/40 hover:border-primary/35 hover:bg-content2/90 flex rounded-xl p-3 no-underline transition-all"
              >
                <div className="min-w-0 flex-1 pr-3">
                  <div className="text-default-foreground flex flex-wrap items-center gap-2 text-sm">
                    <span className="font-mono text-xs sm:text-sm">{tx.sender_account}</span>
                    <span className="text-default-500 text-xs">{tx.sender_bank}</span>
                    <ArrowRight2 size={14} variant="Linear" className="text-default-600 shrink-0" />
                    <span className="font-mono text-xs sm:text-sm">{tx.receiver_account}</span>
                    <span className="text-default-500 text-xs">{tx.receiver_bank}</span>
                  </div>
                  <p className="text-default-600 mt-2 font-mono text-[0.7rem]">{timeAgo(tx.created_at)}</p>
                </div>
                <div className="flex shrink-0 flex-col items-end gap-2 text-right">
                  <p className="text-default-foreground text-sm font-bold">{fmt.format(tx.amount_naira ?? 0)}</p>
                  {tx.risk_score > 0 ? (
                    <p className="text-warning font-mono text-xs">Risk {(Number(tx.risk_score) * 100).toFixed(0)}%</p>
                  ) : null}
                  <div className="flex items-center gap-2">
                    {(tx.status === "held" || tx.status === "escalated") && <Radar2 size={14} variant="Bold" className="text-danger" />}
                    <Chip size="sm" variant="flat" color={statusChipColor(tx.status)} className="font-mono text-[0.65rem] uppercase">
                      {tx.status || "—"}
                    </Chip>
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
        {!transactionsLoading && rows.length === 0 ? (
          <div className="text-default-500 px-4 py-12 text-center text-sm leading-relaxed">
            No transactions in this view.
            <br />
            <span className="text-default-600 text-xs">Adjust filters or run the backend simulator.</span>
          </div>
        ) : null}
        </div>
      </Card.Content>
    </Card.Root>
  );
}
