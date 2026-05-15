const STOPWORDS = new Set([
  "what",
  "the",
  "from",
  "between",
  "transfer",
  "opay",
  "link",
  "and",
  "that",
  "this",
  "how",
  "can",
  "you",
  "show",
  "for",
  "with",
  "about",
]);

export function extractQueryTokens(message) {
  const msg = (message || "").toLowerCase();
  const words = msg.match(/[a-z0-9]{3,}/g) || [];
  return [...new Set(words.filter((w) => !STOPWORDS.has(w)))].slice(0, 5);
}

export function buildActiveThoughts({ memory, messages, sending, avatarState }) {
  const thoughts = [];
  if (sending || avatarState === "thinking") {
    thoughts.push({ id: "scan", text: "scanning…", kind: "pulse" });
  }
  if (avatarState === "alert") {
    thoughts.push({ id: "alert", text: "alert signal", kind: "alert" });
  }

  const lastUser = [...(messages || [])].reverse().find((m) => m.role === "user");
  if (lastUser?.content) {
    const snippet = lastUser.content.trim().slice(0, 42);
    if (snippet) thoughts.push({ id: "last", text: snippet, kind: "query" });
    for (const tok of extractQueryTokens(lastUser.content)) {
      thoughts.push({ id: `tok-${tok}`, text: tok, kind: "token" });
    }
  }

  const entities = memory?.entities || [];
  const sorted = [...entities].sort(
    (a, b) => (b.transaction_refs?.length || 0) - (a.transaction_refs?.length || 0)
  );
  for (const ent of sorted.slice(0, 6)) {
    const label = (ent.label || ent.id || "").trim();
    if (label) thoughts.push({ id: `ent-${ent.id}`, text: label, kind: "entity" });
  }

  const links = memory?.links || [];
  for (const link of links.filter((l) => l.source !== l.target).slice(0, 3)) {
    const type = (link.type || "link").replace(/_/g, " ");
    thoughts.push({ id: `link-${link.type}-${link.source}`, text: type, kind: "link" });
  }

  const seen = new Set();
  const unique = [];
  for (const t of thoughts) {
    const key = t.text.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    unique.push(t);
    if (unique.length >= 10) break;
  }
  return unique;
}

const MAX_NODES = 24;

export function buildNeuralGraph(memory) {
  const entities = memory?.entities || [];
  const links = memory?.links || [];
  if (!entities.length) return { nodes: [], edges: [], empty: true };

  const linkedIds = new Set();
  for (const l of links) {
    if (l.source !== l.target) {
      linkedIds.add(l.source);
      linkedIds.add(l.target);
    }
  }

  let pool = entities.filter((e) => linkedIds.has(e.id));
  if (pool.length < 3) pool = entities;
  pool = pool
    .sort((a, b) => (b.transaction_refs?.length || 0) - (a.transaction_refs?.length || 0))
    .slice(0, MAX_NODES);

  const idSet = new Set(pool.map((e) => e.id));
  const cx = 260;
  const cy = 200;
  const r = 118;
  const n = pool.length;

  const nodes = pool.map((ent, i) => {
    const angle = (2 * Math.PI * i) / Math.max(n, 1) - Math.PI / 2;
    const refs = ent.transaction_refs || [];
    return {
      id: ent.id,
      label: truncate(ent.label || ent.id, 18),
      kind: ent.kind || "entity",
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
      weight: refs.length,
      transactionRef: refs[0] || null,
    };
  });

  const nodeById = Object.fromEntries(nodes.map((nd) => [nd.id, nd]));
  const edges = [];
  for (const link of links) {
    if (link.source === link.target) continue;
    if (!idSet.has(link.source) || !idSet.has(link.target)) continue;
    const a = nodeById[link.source];
    const b = nodeById[link.target];
    if (!a || !b) continue;
    edges.push({
      id: `${link.source}-${link.target}-${link.type}`,
      source: link.source,
      target: link.target,
      type: link.type,
      reason: link.reason,
      x1: a.x,
      y1: a.y,
      x2: b.x,
      y2: b.y,
      refs: link.transaction_refs || [],
    });
  }

  return { nodes, edges, empty: nodes.length === 0, cx, cy };
}

function truncate(s, max) {
  if (s.length <= max) return s;
  return `${s.slice(0, max - 1)}…`;
}

/** Polar positions for thought bubbles around the panel (0–1). */
export function bubblePosition(index, total) {
  const angle = (2 * Math.PI * index) / Math.max(total, 1) - Math.PI / 2;
  const rx = 42 + (index % 3) * 4;
  const ry = 38 + (index % 2) * 6;
  return {
    left: `${50 + rx * Math.cos(angle)}%`,
    top: `${48 + ry * Math.sin(angle)}%`,
  };
}
