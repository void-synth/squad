"use client";

import { useId, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Spinner } from "@heroui/react";
import { useAgent } from "../../context/AgentContext.jsx";
import { buildNeuralGraph, bubblePosition } from "./agentNeuralUtils.js";

function coreClass(avatarState, sending) {
  if (sending || avatarState === "thinking") return "titan-neural-core titan-neural-core--thinking";
  if (avatarState === "alert") return "titan-neural-core titan-neural-core--alert";
  return "titan-neural-core";
}

export default function AgentNeural() {
  const router = useRouter();
  const { memory, memoryLoading, activeThoughts, avatarState, sending } = useAgent();
  const uid = useId().replace(/:/g, "");
  const gradNode = `neuralNode-${uid}`;
  const gradEdge = `neuralEdge-${uid}`;
  const bgGrad = `neuralBg-${uid}`;

  const graph = useMemo(() => buildNeuralGraph(memory), [memory]);
  const [hoverId, setHoverId] = useState(null);

  const edgeActive = (edge) => {
    if (!hoverId) return true;
    return edge.source === hoverId || edge.target === hoverId;
  };

  const nodeDimmed = (nodeId) => {
    if (!hoverId || hoverId === nodeId) return false;
    return !graph.edges.some((e) => edgeActive(e) && (e.source === nodeId || e.target === nodeId));
  };

  if (memoryLoading) {
    return (
      <div className="titan-neural-wrap flex min-h-[420px] items-center justify-center">
        <Spinner color="primary" />
      </div>
    );
  }

  if (graph.empty) {
    return (
      <div className="titan-neural-wrap flex min-h-[420px] flex-col items-center justify-center gap-2 p-6 text-center">
        <p className="text-default-foreground text-sm font-medium">No neural activity yet</p>
        <p className="text-default-500 max-w-sm text-xs">
          Run the backend and <code className="text-primary">python simulate.py</code> to populate memory
          links, then return here.
        </p>
      </div>
    );
  }

  return (
    <div className="titan-neural-wrap relative min-h-[420px] overflow-hidden rounded-xl">
      <div className="text-default-500 mb-2 px-1">
        <span className="text-[0.65rem] font-bold uppercase tracking-[0.14em]">Neural memory</span>
        <span className="mt-0.5 block text-[0.72rem]">
          {graph.nodes.length} nodes · {graph.edges.length} synapses
        </span>
      </div>

      <div className="relative mx-auto max-w-[560px]">
        <svg className="titan-graph-svg titan-neural-svg" viewBox="0 0 520 400" preserveAspectRatio="xMidYMid meet">
          <defs>
            <radialGradient id={bgGrad} cx="50%" cy="50%" r="55%">
              <stop offset="0%" stopColor="rgba(16, 185, 129, 0.12)" />
              <stop offset="100%" stopColor="transparent" />
            </radialGradient>
            <linearGradient id={gradNode} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#6ee7b7" />
              <stop offset="100%" stopColor="#059669" />
            </linearGradient>
            <linearGradient id={gradEdge} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="rgba(16, 185, 129, 0.2)" />
              <stop offset="50%" stopColor="rgba(212, 168, 83, 0.85)" />
              <stop offset="100%" stopColor="rgba(16, 185, 129, 0.2)" />
            </linearGradient>
          </defs>
          <rect width="520" height="400" fill={`url(#${bgGrad})`} />
          {graph.edges.map((edge) => {
            const active = edgeActive(edge);
            return (
              <line
                key={edge.id}
                x1={edge.x1}
                y1={edge.y1}
                x2={edge.x2}
                y2={edge.y2}
                stroke={`url(#${gradEdge})`}
                strokeWidth={active ? 2 : 1}
                strokeOpacity={active ? 0.8 : 0.12}
                strokeDasharray="6 4"
                className={active ? "titan-dash-line" : undefined}
              />
            );
          })}
          {graph.nodes.map((node) => {
            const r = 10 + Math.min(node.weight, 6) * 1.5;
            const active = hoverId === node.id;
            const dim = nodeDimmed(node.id);
            return (
              <g
                key={node.id}
                style={{ cursor: node.transactionRef ? "pointer" : "default" }}
                onMouseEnter={() => setHoverId(node.id)}
                onMouseLeave={() => setHoverId(null)}
                onClick={() => {
                  if (node.transactionRef) {
                    router.push(`/transactions/${encodeURIComponent(node.transactionRef)}`);
                  }
                }}
              >
                {active ? (
                  <circle cx={node.x} cy={node.y} r={r + 8} fill="rgba(16, 185, 129, 0.15)" />
                ) : null}
                <circle cx={node.x} cy={node.y} r={r} fill={`url(#${gradNode})`} opacity={dim ? 0.35 : 1} />
                <text
                  x={node.x}
                  y={node.y + r + 12}
                  textAnchor="middle"
                  fill="currentColor"
                  className="text-default-500 text-[9px] font-medium"
                  opacity={dim ? 0.4 : 1}
                >
                  {node.label}
                </text>
              </g>
            );
          })}
        </svg>

        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <motion.div
            className={coreClass(avatarState, sending)}
            animate={{
              scale: sending || avatarState === "thinking" ? [1, 1.08, 1] : [1, 1.03, 1],
              opacity: [0.85, 1, 0.85],
            }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            <span className="titan-neural-core__label">Titan</span>
          </motion.div>
        </div>

        {activeThoughts.map((thought, i) => {
          const pos = bubblePosition(i, activeThoughts.length);
          return (
            <motion.div
              key={thought.id}
              className={`titan-thought-bubble pointer-events-none titan-thought-bubble--${thought.kind}`}
              style={{ left: pos.left, top: pos.top }}
              initial={{ opacity: 0, scale: 0.85 }}
              animate={{
                opacity: 1,
                scale: 1,
                y: [0, -6, 0],
                x: [0, i % 2 === 0 ? 4 : -4, 0],
              }}
              transition={{
                opacity: { duration: 0.35 },
                scale: { duration: 0.35 },
                y: { duration: 3.5 + i * 0.2, repeat: Infinity, ease: "easeInOut" },
                x: { duration: 4 + i * 0.15, repeat: Infinity, ease: "easeInOut" },
              }}
            >
              {thought.text}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
