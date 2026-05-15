"""Build transaction memory graph for agent Q&A (names, accounts, graph paths)."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.ai.graph_engine import transaction_graph
from app.models.models import FraudAlert, Transaction

# Known demo senders from simulate.py when DB rows lack sender_name
ACCOUNT_NAME_MAP: dict[str, str] = {
    "8011223344": "Bolu Adeyemi",
    "8022334455": "Daniel Okoro",
    "0123456789": "Emeka Okafor",
    "2087654321": "Ngozi Adeyemi",
    "3012345678": "Chidi Nwosu",
}


def normalize_name(name: str) -> str:
    s = (name or "").strip().lower()
    if not s:
        return ""
    return re.sub(r"\s+", " ", s)


def first_token(name: str) -> str:
    n = normalize_name(name)
    return n.split()[0] if n else ""


def tx_to_memory_row(tx: Transaction) -> dict[str, Any]:
    sender_name = (tx.sender_name or "").strip() or ACCOUNT_NAME_MAP.get(tx.sender_account, "")
    gross = float(tx.amount or 0)
    return {
        "id": tx.id,
        "transaction_ref": tx.transaction_ref,
        "amount_naira": gross / 100.0,
        "sender_account": tx.sender_account,
        "receiver_account": tx.receiver_account,
        "sender_bank": tx.sender_bank,
        "receiver_bank": tx.receiver_bank,
        "sender_name": sender_name,
        "receiver_name": tx.receiver_name or "",
        "description": tx.description or "",
        "device_id": tx.device_id or "",
        "status": tx.status,
        "risk_score": float(tx.risk_score or 0),
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
    }


def build_memory(db: Session, limit: int = 500) -> dict[str, Any]:
    rows = db.query(Transaction).order_by(Transaction.created_at.desc()).limit(limit).all()
    transactions = [tx_to_memory_row(t) for t in rows]

    entities: dict[str, dict[str, Any]] = {}
    links: list[dict[str, Any]] = []
    seen_links: set[tuple[str, str, str]] = set()

    def add_entity(key: str, kind: str, label: str, tx_ref: str) -> None:
        if key not in entities:
            entities[key] = {"id": key, "kind": kind, "label": label, "transaction_refs": []}
        if tx_ref not in entities[key]["transaction_refs"]:
            entities[key]["transaction_refs"].append(tx_ref)

    def add_link(a: str, b: str, link_type: str, reason: str, tx_refs: list[str]) -> None:
        pair = (min(a, b), max(a, b), link_type)
        if pair in seen_links:
            return
        seen_links.add(pair)
        links.append(
            {
                "source": a,
                "target": b,
                "type": link_type,
                "reason": reason,
                "transaction_refs": tx_refs[:8],
            }
        )

    by_name: dict[str, list[str]] = {}
    by_account: dict[str, list[str]] = {}
    by_device: dict[str, list[str]] = {}

    for row in transactions:
        ref = row["transaction_ref"]
        sn = normalize_name(row["sender_name"])
        if sn:
            add_entity(f"name:{sn}", "person", row["sender_name"], ref)
            by_name.setdefault(sn, []).append(ref)
        sa = row["sender_account"]
        if sa:
            add_entity(f"acct:{sa}", "account", sa, ref)
            by_account.setdefault(sa, []).append(ref)
        ra = row["receiver_account"]
        if ra:
            add_entity(f"acct:{ra}", "account", ra, ref)
            by_account.setdefault(ra, []).append(ref)
        dev = row["device_id"]
        if dev:
            by_device.setdefault(dev, []).append(ref)

    for name, refs in by_name.items():
        if len(refs) < 2:
            continue
        add_link(f"name:{name}", f"name:{name}", "same_person", f"Multiple transfers as {name}", refs)

    for acct, refs in by_account.items():
        if len(refs) < 2:
            continue
        add_link(f"acct:{acct}", f"acct:{acct}", "same_account", f"Shared account {acct[-4:]}", refs)

    for dev, refs in by_device.items():
        if len(refs) < 2:
            continue
        add_link(f"device:{dev}", f"device:{dev}", "same_device", f"Shared device {dev}", refs)

    # Cross-person links: shared receiver between named senders (e.g. Bolu & Daniel → same OPay wallet)
    ref_to_row = {r["transaction_ref"]: r for r in transactions}
    for i, a_ref in enumerate(transactions):
        a = transactions[i]
        for b in transactions[i + 1 :]:
            if a["receiver_account"] and a["receiver_account"] == b["receiver_account"]:
                an = normalize_name(a["sender_name"])
                bn = normalize_name(b["sender_name"])
                if an and bn and an != bn:
                    add_link(
                        f"name:{an}",
                        f"name:{bn}",
                        "shared_receiver",
                        f"Both sent to {b['receiver_bank']} account …{b['receiver_account'][-4:]}",
                        [a["transaction_ref"], b["transaction_ref"]],
                    )
            if a["device_id"] and a["device_id"] == b["device_id"]:
                an = normalize_name(a["sender_name"])
                bn = normalize_name(b["sender_name"])
                if an and bn and an != bn:
                    add_link(
                        f"name:{an}",
                        f"name:{bn}",
                        "shared_device",
                        f"Same device_id {a['device_id']}",
                        [a["transaction_ref"], b["transaction_ref"]],
                    )

    # Graph path links between sender accounts
    for row in transactions[:80]:
        sa = row["sender_account"]
        if not sa or not transaction_graph.graph.has_node(sa):
            continue
        connected = transaction_graph.get_connected_accounts(sa)
        for other_row in transactions:
            if other_row["transaction_ref"] == row["transaction_ref"]:
                continue
            ob = other_row["sender_account"]
            if any(c["account"] == ob for c in connected):
                an = normalize_name(row["sender_name"])
                bn = normalize_name(other_row["sender_name"])
                if an and bn and an != bn:
                    add_link(
                        f"name:{an}",
                        f"name:{bn}",
                        "graph_path",
                        "Connected in money-hop transfer graph",
                        [row["transaction_ref"], other_row["transaction_ref"]],
                    )

    alerts_q = (
        db.query(FraudAlert)
        .options(joinedload(FraudAlert.transaction))
        .filter(FraudAlert.alert_level >= 2)
        .order_by(FraudAlert.created_at.desc())
        .limit(50)
    )
    alerts = []
    for a in alerts_q:
        t = a.transaction
        alerts.append(
            {
                "id": a.id,
                "risk_score": float(a.risk_score),
                "pattern_type": a.pattern_type,
                "reason": a.reason,
                "transaction_ref": t.transaction_ref if t else "",
                "sender_name": (t.sender_name or ACCOUNT_NAME_MAP.get(t.sender_account, "")) if t else "",
            }
        )

    return {
        "transactions": transactions,
        "links": links,
        "entities": list(entities.values()),
        "alerts": alerts,
    }


def extract_query_tokens(message: str) -> list[str]:
    """Pull likely person names and bank keywords from user message."""
    msg = message.lower()
    tokens: list[str] = []
    for word in re.findall(r"[a-z]{3,}", msg):
        if word in ("what", "the", "from", "between", "transfer", "opay", "link", "and", "that", "this"):
            continue
        tokens.append(word)
    for bank in ("opay", "palmpay", "kuda", "gtbank", "zenith", "uba", "access"):
        if bank in msg:
            tokens.append(bank)
    return list(dict.fromkeys(tokens))


def resolve_query_context(memory: dict[str, Any], message: str) -> dict[str, Any]:
    tokens = extract_query_tokens(message)
    if not tokens:
        return {
            "transactions": memory["transactions"][:40],
            "links": memory["links"][:30],
            "alerts": memory["alerts"][:10],
        }

    matched_txs: list[dict[str, Any]] = []
    for row in memory["transactions"]:
        hay = " ".join(
            [
                normalize_name(row.get("sender_name", "")),
                row.get("sender_bank", ""),
                row.get("receiver_bank", ""),
                row.get("description", ""),
                row.get("transaction_ref", ""),
            ]
        ).lower()
        if any(tok in hay for tok in tokens):
            matched_txs.append(row)

    matched_links = []
    for link in memory["links"]:
        blob = (link.get("reason", "") + " ".join(link.get("transaction_refs", []))).lower()
        if any(tok in blob for tok in tokens):
            matched_links.append(link)
        else:
            for ref in link.get("transaction_refs", []):
                if any(t["transaction_ref"] == ref for t in matched_txs):
                    matched_links.append(link)
                    break

    if not matched_txs:
        matched_txs = memory["transactions"][:25]
    if not matched_links:
        matched_links = memory["links"][:20]

    return {
        "transactions": matched_txs[:50],
        "links": matched_links[:40],
        "alerts": memory["alerts"][:10],
        "query_tokens": tokens,
    }
