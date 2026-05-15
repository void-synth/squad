"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Button, Card, Chip, Spinner } from "@heroui/react";
import { ArrowRight2, Flash, Radar2 } from "../../icons/isax.jsx";
import { useDashboard } from "../../context/DashboardContext.jsx";

const PAGE_SIZE = 10;

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
    highlightedRef,
  } = useDashboard();
  const listRef = useRef(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [transactionStatusFilter]);

  const count = transactions.length;
  const rows = useMemo(() => transactions, [transactions]);
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));

  useEffect(() => {
    setPage((p) => Math.min(Math.max(1, p), totalPages));
  }, [totalPages]);

  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [page, transactionStatusFilter, rows.length]);

  const displayedRows = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return rows.slice(start, start + PAGE_SIZE);
  }, [rows, page]);

  return (
    <Card.Root className="flex flex-col rounded-2xl border border-default-200/80 bg-content1/80 shadow-sm backdrop-blur-sm">
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

      <Card.Content className="relative flex flex-col p-0">
        {transactionsLoading ? (
          <div className="bg-content1/60 absolute inset-0 z-[1] flex items-center justify-center gap-3 backdrop-blur-sm">
            <Spinner color="primary" size="md" />
            <span className="text-default-500 text-sm">Loading…</span>
          </div>
        ) : null}
        <div ref={listRef} className="p-2 sm:p-3">
        <div className="flex flex-col gap-2">
          {displayedRows.map((tx) => {
            const ref = tx.transaction_ref || tx.id;
            const to = `/transactions/${encodeURIComponent(String(ref))}`;
            return (
              <Link
                key={String(ref)}
                href={to}
                className={[
                  "group flex rounded-xl border p-3 no-underline transition-all",
                  highlightedRef === String(ref)
                    ? "border-warning bg-warning/10 ring-2 ring-warning/40"
                    : "border-default-200/60 bg-content2/40 hover:border-primary/35 hover:bg-content2/90",
                ].join(" ")}
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
                  {tx.platform_fee_naira != null && tx.net_settlement_naira != null ? (
                    <p className="text-default-500 max-w-[11rem] text-right text-[0.65rem] leading-snug">
                      Fee {fmt.format(tx.platform_fee_naira)} · Net {fmt.format(tx.net_settlement_naira)}
                    </p>
                  ) : null}
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

        {!transactionsLoading && totalPages > 1 ? (
          <div className="border-default-200/70 bg-content1/95 flex shrink-0 flex-wrap items-center justify-between gap-2 border-t px-3 py-2.5 sm:px-4">
            <span className="text-default-500 text-xs tabular-nums">
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, count)} of {count.toLocaleString()}
            </span>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                radius="lg"
                variant="bordered"
                className="min-w-[5.5rem] font-semibold"
                isDisabled={page <= 1}
                onPress={() => setPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="text-default-600 px-1 text-xs font-semibold tabular-nums">
                {page} / {totalPages}
              </span>
              <Button
                size="sm"
                radius="lg"
                variant="bordered"
                className="min-w-[5.5rem] font-semibold"
                isDisabled={page >= totalPages}
                onPress={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </Button>
            </div>
          </div>
        ) : null}
      </Card.Content>
    </Card.Root>
  );
}
