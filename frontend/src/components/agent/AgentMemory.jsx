"use client";

import { Spinner } from "@heroui/react";
import Link from "next/link";
import { useAgent } from "../../context/AgentContext.jsx";

const fmt = new Intl.NumberFormat("en-NG", { style: "currency", currency: "NGN", maximumFractionDigits: 0 });

export default function AgentMemory() {
  const { memory, memoryLoading } = useAgent();

  if (memoryLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner color="primary" />
      </div>
    );
  }

  const txs = memory?.transactions || [];
  const links = memory?.links || [];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section className="border-default-200/60 rounded-xl border bg-content2/30 p-3">
        <h3 className="text-default-foreground mb-2 text-sm font-semibold">Scanned transfers ({txs.length})</h3>
        <ul className="max-h-[420px] space-y-2 overflow-y-auto">
          {txs.map((tx) => (
            <li key={tx.transaction_ref} className="border-default-200/50 rounded-lg border bg-content1/80 p-2 text-xs">
              <Link href={`/transactions/${encodeURIComponent(tx.transaction_ref)}`} className="text-primary font-mono hover:underline">
                {tx.transaction_ref}
              </Link>
              <p className="text-default-foreground mt-1 font-medium">
                {(tx.sender_name || "Unknown")} → {tx.receiver_bank} …{String(tx.receiver_account).slice(-4)}
              </p>
              <p className="text-default-500">
                {fmt.format(tx.amount_naira ?? 0)} · {tx.status} · risk {((tx.risk_score || 0) * 100).toFixed(0)}%
              </p>
            </li>
          ))}
          {txs.length === 0 ? <p className="text-default-500 text-sm">No transactions yet. Run simulate.py.</p> : null}
        </ul>
      </section>
      <section className="border-default-200/60 rounded-xl border bg-content2/30 p-3">
        <h3 className="text-default-foreground mb-2 text-sm font-semibold">Connections ({links.length})</h3>
        <ul className="max-h-[420px] space-y-2 overflow-y-auto">
          {links.map((link, i) => (
            <li key={`${link.type}-${i}`} className="border-default-200/50 rounded-lg border bg-content1/80 p-2 text-xs">
              <p className="text-primary font-mono uppercase">{link.type}</p>
              <p className="text-default-600 mt-1">{link.reason}</p>
              <p className="text-default-500 mt-1 font-mono">{(link.transaction_refs || []).join(", ")}</p>
            </li>
          ))}
          {links.length === 0 ? <p className="text-default-500 text-sm">Links appear when names or accounts overlap.</p> : null}
        </ul>
      </section>
    </div>
  );
}
