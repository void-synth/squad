"use client";

import { useMemo } from "react";
import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  Tooltip,
} from "chart.js";
import { Bar } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

ChartJS.defaults.font.family = '"Satoshi", ui-sans-serif, system-ui';

function maxStacked(buckets) {
  let m = 0;
  for (const b of buckets) {
    m = Math.max(m, (Number(b.safe) || 0) + (Number(b.flagged) || 0));
  }
  return m;
}

/**
 * Stacked throughput bars — solid colors, explicit Y max when empty, numeric borderRadius
 * (per-corner radii on stacked bars often fail to paint in Chart.js → “blank white” chart).
 */
export default function ThroughputBarChart({ buckets }) {
  const suggestedY = useMemo(() => {
    const m = maxStacked(buckets);
    return Math.max(1, m);
  }, [buckets]);

  const data = useMemo(
    () => ({
      labels: buckets.map((b) => b.label),
      datasets: [
        {
          label: "Safe",
          data: buckets.map((b) => b.safe),
          backgroundColor: "#10b981",
          borderColor: "#047857",
          borderWidth: 1,
          borderRadius: 4,
          stack: "throughput",
        },
        {
          label: "Flagged / held",
          data: buckets.map((b) => b.flagged),
          backgroundColor: "#f43f5e",
          borderColor: "#be123c",
          borderWidth: 1,
          borderRadius: 4,
          stack: "throughput",
        },
      ],
    }),
    [buckets]
  );

  const options = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      layout: {
        padding: { top: 6, right: 4, bottom: 0, left: 4 },
      },
      plugins: {
        legend: {
          position: "bottom",
          align: "start",
          labels: {
            boxWidth: 10,
            boxHeight: 10,
            padding: 8,
            font: { size: 11, weight: "500" },
            color: "#475569",
            usePointStyle: true,
            pointStyle: "rectRounded",
          },
        },
        tooltip: {
          backgroundColor: "#ffffff",
          titleColor: "#0f172a",
          bodyColor: "#334155",
          borderColor: "#e2e8f0",
          borderWidth: 1,
          padding: 10,
          cornerRadius: 10,
          displayColors: true,
          callbacks: {
            footer: (tooltipItems) => {
              const sum = tooltipItems.reduce((acc, it) => acc + (Number(it.parsed?.y) || 0), 0);
              return sum ? `Total: ${sum}` : "";
            },
          },
        },
      },
      scales: {
        x: {
          stacked: true,
          grid: { display: false, drawOnChartArea: false },
          ticks: {
            maxRotation: 0,
            autoSkip: true,
            maxTicksLimit: 12,
            font: { size: 10, family: "JetBrains Mono, ui-monospace, monospace" },
            color: "#64748b",
          },
          border: { display: true, color: "#e2e8f0" },
        },
        y: {
          stacked: true,
          beginAtZero: true,
          suggestedMax: suggestedY,
          grace: "8%",
          ticks: {
            precision: 0,
            maxTicksLimit: 6,
            font: { size: 10 },
            color: "#64748b",
          },
          grid: {
            color: "rgba(148, 163, 184, 0.45)",
            drawBorder: false,
            lineWidth: 1,
            borderDash: [4, 4],
          },
          border: { display: true, color: "#e2e8f0", dash: [4, 4] },
        },
      },
    }),
    [suggestedY]
  );

  return (
    <div className="h-[200px] w-full min-h-[200px] min-w-0">
      <Bar data={data} options={options} />
    </div>
  );
}
