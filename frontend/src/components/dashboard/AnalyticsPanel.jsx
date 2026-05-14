"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Card, Chip } from "@heroui/react";
import { Activity, Chart2, Danger, SecuritySafe, TickCircle, WalletMoney } from "../../icons/isax.jsx";
import { useDashboard } from "../../context/DashboardContext.jsx";
import ThroughputBarChart from "./ThroughputBarChart.jsx";

function formatCompactNaira(n) {
  const v = Number(n) || 0;
  if (v >= 1e9) return `₦${(v / 1e9).toFixed(1)}B`;
  if (v >= 1e6) return `₦${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `₦${(v / 1e3).toFixed(0)}K`;
  return `₦${v.toFixed(0)}`;
}

function useAnimatedNumber(target, duration = 800) {
  const [val, setVal] = useState(0);
  const startRef = useRef(null);
  const fromRef = useRef(0);

  useEffect(() => {
    const from = fromRef.current;
    const to = Number(target) || 0;
    startRef.current = null;
    let frame;
    const step = (ts) => {
      if (startRef.current == null) startRef.current = ts;
      const p = Math.min(1, (ts - startRef.current) / duration);
      const eased = 1 - (1 - p) ** 3;
      setVal(from + (to - from) * eased);
      if (p < 1) frame = requestAnimationFrame(step);
      else fromRef.current = to;
    };
    frame = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frame);
  }, [target, duration]);

  return val;
}

function HoldsReleasesCard({ held, released, compact }) {
  return (
    <Card.Root className="rounded-2xl border border-default-200/80 bg-content1/80 shadow-sm backdrop-blur-sm border-t-4 border-t-primary">
      <Card.Content className={compact ? "gap-2 p-3" : "gap-3 p-4"}>
        <div className={`text-default-500 flex items-center gap-2 ${compact ? "mb-0" : "mb-0.5"}`}>
          <SecuritySafe size={compact ? 16 : 18} variant="Bold" className="text-primary" />
          <span className={`font-bold uppercase tracking-wider ${compact ? "text-[0.6rem]" : "text-[0.65rem]"}`}>Holds & releases</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <p className={`text-default-500 font-medium uppercase tracking-wide ${compact ? "text-[0.55rem]" : "text-[0.6rem]"}`}>Held</p>
            <p className={`text-default-foreground font-bold tabular-nums ${compact ? "text-lg" : "text-2xl"}`}>{Math.round(held).toLocaleString()}</p>
            <p className={`text-default-500 leading-tight ${compact ? "text-[0.6rem]" : "text-xs"}`}>Active L3</p>
          </div>
          <div>
            <p className={`text-default-500 font-medium uppercase tracking-wide ${compact ? "text-[0.55rem]" : "text-[0.6rem]"}`}>Released</p>
            <p className={`text-default-foreground font-bold tabular-nums ${compact ? "text-lg" : "text-2xl"}`}>{Math.round(released).toLocaleString()}</p>
            <p className={`text-default-500 leading-tight ${compact ? "text-[0.6rem]" : "text-xs"}`}>Analyst cleared</p>
          </div>
        </div>
      </Card.Content>
    </Card.Root>
  );
}

const ACCENT = {
  neutral: "border-t-default-300",
  primary: "border-t-primary",
  warning: "border-t-warning",
  danger: "border-t-danger",
  success: "border-t-success",
};

function StatCard({ title, value, subtitle, accent, icon: Icon, compact }) {
  return (
    <Card.Root className={`rounded-2xl border border-default-200/80 bg-content1/80 shadow-sm backdrop-blur-sm border-t-4 ${ACCENT[accent] || ACCENT.neutral}`}>
      <Card.Content className={compact ? "gap-0.5 p-3" : "gap-1 p-4"}>
        <div className={`text-default-500 flex items-center gap-2 ${compact ? "mb-0.5" : "mb-1"}`}>
          {Icon ? <Icon size={compact ? 16 : 18} variant="Bold" className="text-primary" /> : null}
          <span className={`font-bold uppercase tracking-wider ${compact ? "text-[0.6rem]" : "text-[0.65rem]"}`}>{title}</span>
        </div>
        <p className={`text-default-foreground font-bold tracking-tight ${compact ? "text-lg" : "text-2xl"}`}>{value}</p>
        <p className={`text-default-500 leading-snug ${compact ? "text-[0.65rem]" : "text-xs"}`}>{subtitle}</p>
      </Card.Content>
    </Card.Root>
  );
}

export default function AnalyticsPanel({ layout = "default" }) {
  const { transactions, stats, isConnected } = useDashboard();

  const txMonitored = useAnimatedNumber(stats.total_transactions ?? 0);
  const threats = useAnimatedNumber(stats.total_flagged ?? 0);
  const intercepted = useAnimatedNumber(stats.total_naira_intercepted ?? 0);
  const fpr = useAnimatedNumber(stats.false_positive_rate ?? 0);
  const held = useAnimatedNumber(stats.total_held ?? 0);
  const released = useAnimatedNumber(stats.total_released ?? 0);
  const reserve = useAnimatedNumber(stats.total_platform_fee_naira ?? 0);
  const feeRateRaw = Number(stats.platform_fee_rate);
  const feeRatePct = ((Number.isFinite(feeRateRaw) ? feeRateRaw : 0.05) * 100).toFixed(0);
  const topFlagged = Array.isArray(stats.top_flagged_accounts) ? stats.top_flagged_accounts : [];

  const chartData = useMemo(() => {
    const now = Date.now();
    const buckets = Array.from({ length: 10 }, (_, i) => {
      const t = new Date(now - (9 - i) * 60_000);
      return {
        label: `${t.getHours().toString().padStart(2, "0")}:${t.getMinutes().toString().padStart(2, "0")}`,
        safe: 0,
        flagged: 0,
        key: t.getTime(),
      };
    });
    for (const tx of transactions) {
      const ts = tx.created_at ? new Date(tx.created_at).getTime() : now;
      const diffMin = Math.floor((now - ts) / 60_000);
      if (diffMin < 0 || diffMin > 9) continue;
      const idx = 9 - diffMin;
      if (tx.status === "flagged" || tx.status === "held" || tx.status === "escalated") {
        buckets[idx].flagged += 1;
      } else {
        buckets[idx].safe += 1;
      }
    }
    return buckets;
  }, [transactions]);

  const fprAccent = fpr < 5 ? "success" : fpr <= 10 ? "warning" : "danger";
  const workspace = layout === "workspace";

  return (
    <div className={workspace ? "flex flex-col gap-3" : "flex flex-col gap-4"}>
      <div className={workspace ? "grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6 lg:gap-3" : "grid grid-cols-2 gap-3 sm:grid-cols-3"}>
        <StatCard
          title="Transactions"
          value={Math.round(txMonitored).toLocaleString()}
          subtitle="Monitored volume"
          accent="neutral"
          icon={Activity}
          compact={workspace}
        />
        <StatCard
          title="Threats"
          value={Math.round(threats).toLocaleString()}
          subtitle="Flagged by engine"
          accent="warning"
          icon={Danger}
          compact={workspace}
        />
        <StatCard
          title="Intercepted"
          value={formatCompactNaira(intercepted)}
          subtitle="Holds (₦)"
          accent="danger"
          icon={WalletMoney}
          compact={workspace}
        />
        <StatCard
          title="Titan reserve"
          value={formatCompactNaira(reserve)}
          subtitle={`Simulated ${feeRatePct}% platform fee`}
          accent="success"
          icon={Chart2}
          compact={workspace}
        />
        <StatCard
          title="False positive"
          value={`${fpr.toFixed(1)}%`}
          subtitle="Released / held"
          accent={fprAccent}
          icon={TickCircle}
          compact={workspace}
        />
        <HoldsReleasesCard held={held} released={released} compact={workspace} />
      </div>

      {topFlagged.length > 0 ? (
        <Card.Root className="rounded-2xl border border-default-200/80 bg-content1/60 p-4 shadow-sm backdrop-blur-sm">
          <p className="text-default-500 mb-3 text-[0.65rem] font-bold uppercase tracking-widest">Top flagged senders</p>
          <div className="flex flex-wrap gap-2">
            {topFlagged.map((row) => (
              <Chip key={row.sender_account} size="sm" variant="bordered" color="warning" className="font-mono text-xs">
                {row.flags} · {String(row.sender_account).slice(0, 12)}
                {String(row.sender_account).length > 12 ? "…" : ""}
              </Chip>
            ))}
          </div>
        </Card.Root>
      ) : null}

      <Card.Root className="rounded-2xl border border-default-200/80 bg-content1/80 p-4 shadow-sm backdrop-blur-sm">
        <div className="mb-3 flex items-baseline justify-between gap-2">
          <div>
            <Card.Title className="text-default-foreground text-sm font-semibold">Throughput</Card.Title>
            <Card.Description className="text-default-500 text-xs">Last 10 minutes · safe vs flagged</Card.Description>
          </div>
          <Chip size="sm" variant="flat" color={isConnected ? "success" : "default"} className="uppercase">
            {isConnected ? "Live" : "Paused"}
          </Chip>
        </div>
        <ThroughputBarChart buckets={chartData} />
      </Card.Root>
    </div>
  );
}
