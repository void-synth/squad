/** Normalize REST + Socket.IO alert payloads to one dashboard shape. */

export function normalizeAlert(raw) {
  if (!raw) return null;
  const id = raw.alert_id ?? raw.id;
  if (id == null) return null;
  const tx = raw.transaction || {};
  const ref = raw.transaction_ref || tx.transaction_ref || "";
  return {
    id,
    alert_id: id,
    risk_score: Number(raw.risk_score ?? 0),
    alert_level: Number(raw.alert_level ?? 0),
    reason: raw.reason ?? "",
    pattern_type: raw.pattern_type ?? "",
    action_taken: raw.action_taken ?? "",
    resolved_at: raw.resolved_at ?? null,
    resolved_by: raw.resolved_by ?? "",
    created_at: raw.created_at ?? null,
    transaction_ref: ref,
    sender_account: raw.sender_account ?? tx.sender_account ?? "",
    sender_bank: raw.sender_bank ?? tx.sender_bank ?? "",
    receiver_account: raw.receiver_account ?? tx.receiver_account ?? "",
    receiver_bank: raw.receiver_bank ?? tx.receiver_bank ?? "",
    amount_naira: Number(raw.amount_naira ?? tx.amount_naira ?? 0),
    transaction:
      Object.keys(tx).length > 0
        ? tx
        : ref
          ? { transaction_ref: ref, amount_naira: Number(raw.amount_naira ?? 0) }
          : null,
  };
}

/** Prefer pinned row; else latest unresolved L3, else latest unresolved L2. */
export function pickDisplayedAlert(alerts, pinnedId) {
  const list = Array.isArray(alerts) ? alerts.map((a) => normalizeAlert(a)).filter(Boolean) : [];
  if (pinnedId != null) {
    const pinned = list.find((a) => a.id === pinnedId);
    if (pinned) return pinned;
  }
  const open = list.filter((a) => !a.resolved_at);
  const byTime = [...open].sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
  const hold = byTime.find((a) => a.alert_level >= 3);
  if (hold) return hold;
  return byTime.find((a) => a.alert_level === 2) || null;
}
