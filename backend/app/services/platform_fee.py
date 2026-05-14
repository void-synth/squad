"""Simulated Titan platform fee on gross amounts (Squad-sourced kobo in DB)."""

from __future__ import annotations

from typing import Any

from app.core.config import settings


def _gross_kobo(value: float) -> float:
    return max(0.0, float(value or 0.0))


def settlement_breakdown_gross_kobo(gross_kobo: float) -> dict[str, Any]:
    """Per-transaction split: fee to internal reserve vs net settlement (remainder)."""
    g = _gross_kobo(gross_kobo)
    rate = float(settings["TITAN_PLATFORM_FEE_RATE"])
    fee_kobo = round(g * rate)
    net_kobo = max(0.0, g - fee_kobo)
    acct = str(settings["TITAN_FEE_RECEIVER_ACCOUNT"] or "TITAN_OPS_RESERVE").strip() or "TITAN_OPS_RESERVE"
    return {
        "gross_kobo": g,
        "platform_fee_kobo": float(fee_kobo),
        "net_settlement_kobo": net_kobo,
        "fee_rate": rate,
        "fee_receiver_account": acct,
        "amount_gross_naira": g / 100.0,
        "platform_fee_naira": fee_kobo / 100.0,
        "net_settlement_naira": net_kobo / 100.0,
    }


def summary_fee_fields(gross_kobo: float) -> dict[str, Any]:
    """Flat keys for list/detail summaries and websocket payloads."""
    s = settlement_breakdown_gross_kobo(gross_kobo)
    return {
        "amount_gross_naira": s["amount_gross_naira"],
        "platform_fee_naira": s["platform_fee_naira"],
        "net_settlement_naira": s["net_settlement_naira"],
        "platform_fee_rate": s["fee_rate"],
        "platform_fee_receiver_account": s["fee_receiver_account"],
    }
