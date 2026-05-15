"""Map Squad dashboard webhook JSON into Titan's flat queue / Transaction shape.

Supports:
- Local ``simulate.py`` payloads (``transaction_ref``, ``amount`` in kobo, bank fields).
- Official-style VA / payment events (``transaction_reference``, ``principal_amount`` in Naira, etc.).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _first_dict(*candidates: Any) -> dict[str, Any]:
    for c in candidates:
        if isinstance(c, dict):
            return c
    return {}


def _pick_str(d: dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        v = d.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return default


def _parse_amount_kobo(merged: dict[str, Any]) -> float:
    """Resolve amount as kobo for DB. Official VA fields are in Naira; large bare ints may be kobo."""
    principal = merged.get("principal_amount")
    settled = merged.get("settled_amount")
    for raw in (principal, settled):
        if raw is None:
            continue
        s = str(raw).strip().replace(",", "")
        try:
            naira = float(s)
        except ValueError:
            continue
        return round(naira * 100.0, 4)

    raw = merged.get("amount")
    if raw is None:
        return 0.0
    if isinstance(raw, (int, float)):
        f = float(raw)
        if f >= 1_000_000.0:
            return f
        return round(f * 100.0, 4)
    s = str(raw).strip().replace(",", "")
    try:
        naira = float(s)
    except ValueError:
        logger.warning("Could not parse amount from webhook: %r", raw)
        return 0.0
    return round(naira * 100.0, 4)


def normalize_squad_webhook_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """
    Produce a flat dict suitable for ``Transaction`` + Redis queue.

    Returns None if no transaction reference can be resolved.
    """
    if not isinstance(payload, dict):
        return None

    # --- Already Titan / simulate flat shape ---
    if payload.get("transaction_ref") and (
        "sender_account" in payload or "receiver_account" in payload or payload.get("amount") is not None
    ):
        out = {k: v for k, v in payload.items() if not str(k).startswith("_")}
        out.setdefault("sender_account", out.get("sender_account", ""))
        out.setdefault("receiver_account", out.get("receiver_account", ""))
        out.setdefault("sender_bank", out.get("sender_bank", ""))
        out.setdefault("receiver_bank", out.get("receiver_bank", ""))
        out.setdefault("description", out.get("description", ""))
        out.setdefault("device_id", out.get("device_id", ""))
        out.setdefault("bvn", out.get("bvn", ""))
        out.setdefault("receiver_is_new", bool(out.get("receiver_is_new", False)))
        out.setdefault("sender_name", out.get("sender_name", ""))
        out.setdefault("receiver_name", out.get("receiver_name", ""))
        if out.get("transaction_ref"):
            return out

    # --- Official Squad-style (VA credit, etc.) ---
    data = _first_dict(payload.get("data"))
    merged: dict[str, Any] = {**data, **payload}

    ref = _pick_str(merged, "transaction_ref", "transaction_reference", "TransactionRef", "reference")
    if not ref:
        return None

    amount_kobo = _parse_amount_kobo(merged)

    va = _pick_str(merged, "virtual_account_number", "VirtualAccountNumber")
    cust = _pick_str(merged, "customer_identifier", "CustomerIdentifier")
    channel = _pick_str(merged, "channel", "Channel", default="squad")
    remarks = _pick_str(merged, "remarks", "Remarks", "description", "Description")

    # Credit hits the VA: treat VA as receiver; counterparty is generic unless parsed later.
    receiver_account = va or _pick_str(merged, "receiver_account", "account_number")
    receiver_bank = channel or "Squad"
    sender_account = cust or _pick_str(merged, "sender_account", "depositor_name", default="EXTERNAL")
    sender_bank = _pick_str(merged, "sender_bank", "SenderBank", default="Unknown")

    return {
        "transaction_ref": ref,
        "amount": float(amount_kobo),
        "sender_account": sender_account[:64],
        "receiver_account": receiver_account[:64],
        "sender_bank": sender_bank[:128] or "Unknown",
        "receiver_bank": receiver_bank[:128] or "Squad",
        "description": (remarks or f"Squad {channel}")[:512],
        "device_id": _pick_str(merged, "device_id", "DeviceId")[:128],
        "bvn": _pick_str(merged, "bvn", "BVN")[:32],
        "receiver_is_new": bool(merged.get("receiver_is_new", False)),
        "sender_name": _pick_str(merged, "sender_name", "SenderName", "customer_name")[:128],
        "receiver_name": _pick_str(merged, "receiver_name", "ReceiverName")[:128],
    }
