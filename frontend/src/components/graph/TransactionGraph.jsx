import { useEffect, useId, useMemo, useState } from "react";
import { Spinner } from "@heroui/react";
import { getTransactionDetail } from "../../services/api.js";

function clamp(x, a, b) {
  return Math.max(a, Math.min(b, x));
}

export default function TransactionGraph({ graphData }) {
  const uid = useId().replace(/:/g, "");
  const markerId = `ssArr-${uid}`;
  const gradHub = `ssHub-${uid}`;
  const bgGrad = `ssBg-${uid}`;
  const edgRisk = `ssEdgeRisk-${uid}`;
  const nodeMule = `ssNodeMule-${uid}`;
  const nodeNorm = `ssNodeNorm-${uid}`;
  const glowF = `ssGlow-${uid}`;
  const empty = !graphData || !graphData.nodes || graphData.nodes.length === 0;

  const layout = useMemo(() => {
    if (empty) return { nodes: [], edges: [] };
    const nodes = graphData.nodes;
    const edges = graphData.edges || [];
    const n = nodes.length;
    const cx = 260;
    const cy = 200;
    const r = 118;
    return {
      nodes: nodes.map((node, i) => {
        const angle = (2 * Math.PI * i) / Math.max(n, 1) - Math.PI / 2;
        return {
          ...node,
          x: cx + r * Math.cos(angle),
          y: cy + r * Math.sin(angle),
        };
      }),
      edges,
      cx,
      cy,
    };
  }, [graphData, empty]);

  const [hover, setHover] = useState(null);

  if (empty) {
    return (
      <div>
        <div className="text-default-500 mb-2 text-[0.65rem] font-bold uppercase tracking-[0.14em]">Money-hop network</div>
        <div className="border-default-300/50 from-content2/30 flex h-[280px] flex-col items-center justify-center gap-3 rounded-2xl border border-dashed bg-gradient-to-b to-transparent">
          <Spinner size="md" color="primary" />
          <p className="text-default-500 text-sm">Awaiting graph edges for this sender…</p>
        </div>
      </div>
    );
  }

  const maxAmt = Math.max(...layout.edges.map((e) => e.amount || 0), 1);
  const focus = graphData.focus;

  return (
    <div>
      <div className="mb-2.5 flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-default-500 text-[0.65rem] font-bold uppercase tracking-[0.14em]">Money-hop network</div>
          <div className="text-default-500 mt-1 text-[0.72rem]">
            {layout.nodes.length} nodes · {layout.edges.length} flows
          </div>
        </div>
        <div className="text-default-500 flex gap-3 text-[0.62rem]">
          <span>
            <span className="text-danger font-bold">●</span> Hub
          </span>
          <span>
            <span className="text-warning font-bold">●</span> Mule
          </span>
          <span>
            <span className="font-bold text-[#5c6478]">●</span> Normal
          </span>
        </div>
      </div>
      <svg className="titan-graph-svg" viewBox="0 0 520 400" preserveAspectRatio="xMidYMid meet">
        <defs>
          <radialGradient id={bgGrad} cx="50%" cy="35%" r="70%">
            <stop offset="0%" stopColor="rgba(212,168,83,0.1)" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>
          <marker id={markerId} markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">
            <path d="M0,0 L7,3.5 L0,7 Z" fill="#8b92a8" />
          </marker>
          <linearGradient id={gradHub} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ff9a9a" />
            <stop offset="100%" stopColor="#c73e3e" />
          </linearGradient>
          <linearGradient id={nodeMule} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ffd089" />
            <stop offset="100%" stopColor="#c98a2c" />
          </linearGradient>
          <linearGradient id={nodeNorm} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6a7388" />
            <stop offset="100%" stopColor="#3d4454" />
          </linearGradient>
          <linearGradient id={edgRisk} x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="rgba(255,92,92,0.95)" />
            <stop offset="100%" stopColor="rgba(255,92,92,0.2)" />
          </linearGradient>
          <filter id={glowF} x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <rect x="0" y="0" width="520" height="400" fill={`url(#${bgGrad})`} opacity="0.85" />
        {layout.edges.map((e, idx) => {
          const s = layout.nodes.find((n) => n.id === e.source);
          const t = layout.nodes.find((n) => n.id === e.target);
          if (!s || !t) return null;
          const fromHub = s.id === focus || (s.centrality || 0) > 0.6;
          const stroke = fromHub ? `url(#${edgRisk})` : "rgba(100,108,128,0.55)";
          const w = clamp((e.amount / maxAmt) * 5.5, 1.2, 6);
          return (
            <line
              key={`${e.source}-${e.target}-${idx}`}
              x1={s.x}
              y1={s.y}
              x2={t.x}
              y2={t.y}
              stroke={stroke}
              strokeWidth={w}
              strokeDasharray="7 6"
              strokeLinecap="round"
              markerEnd={`url(#${markerId})`}
              className="titan-dash-line"
            />
          );
        })}
        {layout.nodes.map((n) => {
          const c = n.centrality || 0;
          let fill = `url(#${nodeNorm})`;
          let r = 10;
          let filter = undefined;
          if (c > 0.6) {
            fill = `url(#${gradHub})`;
            r = 22;
            filter = `url(#${glowF})`;
          } else if (c >= 0.3) {
            fill = `url(#${nodeMule})`;
            r = 16;
          }
          const bank = (n.label || "").slice(0, 8);
          return (
            <g key={n.id} onMouseEnter={() => setHover(n)} onMouseLeave={() => setHover(null)} style={{ cursor: "default" }}>
              <circle cx={n.x} cy={n.y} r={r + 6} fill="transparent" />
              <circle cx={n.x} cy={n.y} r={r} fill={fill} filter={filter} stroke="rgba(15,23,42,0.12)" strokeWidth="1" />
              <text x={n.x} y={n.y + r + 16} textAnchor="middle" fill="#71717a" fontSize="10" fontFamily="var(--font-mono)">
                {bank}
              </text>
            </g>
          );
        })}
        {hover ? (
          <g>
            <rect x="288" y="52" width="214" height="108" rx="10" fill="rgba(255,255,255,0.97)" stroke="rgba(15,23,42,0.1)" />
            <text x="302" y="78" fill="#18181b" fontSize="11" fontFamily="var(--font-mono)">
              {hover.id.length > 22 ? `${hover.id.slice(0, 10)}…${hover.id.slice(-8)}` : hover.id}
            </text>
            <text x="302" y="100" fill="#64748b" fontSize="10" fontFamily="var(--font-mono)">
              Centrality {(hover.centrality * 100).toFixed(1)}%
            </text>
          </g>
        ) : null}
      </svg>
    </div>
  );
}

export function useAlertGraph(transactionRef) {
  const [graphData, setGraphData] = useState(null);
  useEffect(() => {
    let cancelled = false;
    if (!transactionRef) {
      setGraphData(null);
      return undefined;
    }
    (async () => {
      try {
        const detail = await getTransactionDetail(transactionRef);
        if (!cancelled) setGraphData(detail.graph_data || { nodes: [], edges: [] });
      } catch {
        if (!cancelled) setGraphData({ nodes: [], edges: [] });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [transactionRef]);
  return graphData;
}
