"""
HTTP client for Squad sandbox APIs.

Base URL: ``SQUAD_BASE_URL`` (default ``https://sandbox-api-d.squadco.com``).

See https://docs.squadco.com/ — parity targets:

- ``POST /virtual-account`` — VA issuance (optional ``email`` in body).
- ``GET /transaction/verify/{transaction_ref}`` — verify payment (path segment URL-encoded).
- ``POST /payout/account/lookup`` — resolve account name before transfer (Transfer API).
- ``POST /payout/transfer`` — Fund Transfer (Squad fields: ``transaction_reference``,
  ``amount`` string kobo, ``currency_id``, ``remark``, ``account_name``, …).
- ``POST /transaction/initiate`` — inline checkout (Squad Payments API); returns a checkout URL.

INTERCEPTION (honest demo behaviour):
We do NOT call a "freeze funds" API on Squad — that endpoint does not exist
in this integration. Real interception is modelled by **not** calling payout
(`initiate_transfer`) for suspicious flows; only "safe" paths would trigger
outbound settlement in a full bank stack. `hold_transaction` updates our own
DB/audit trail to simulate a core-banking hold after our engine flags risk.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from urllib.parse import quote

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import AuditLog, Transaction

logger = logging.getLogger(__name__)


def _extract_squad_checkout_url(payload: Any) -> str | None:
    """Resolve checkout / auth URL from varied Squad response envelopes."""

    def walk(obj: Any) -> str | None:
        if isinstance(obj, str) and obj.startswith("http") and len(obj) > 12:
            return obj
        if not isinstance(obj, dict):
            return None
        for key in (
            "checkout_url",
            "checkout_link",
            "auth_url",
            "authorization_url",
            "payment_url",
            "url",
            "link",
        ):
            v = obj.get(key)
            if isinstance(v, str) and v.startswith("http"):
                return v
        nested = obj.get("data")
        if nested is not None:
            got = walk(nested)
            if got:
                return got
        return None

    return walk(payload)


class SquadClient:
    def __init__(self) -> None:
        self.secret = settings["SQUAD_SECRET_KEY"]
        self.public = settings["SQUAD_PUBLIC_KEY"]
        self.base = settings["SQUAD_BASE_URL"].rstrip("/")
        headers = {
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }
        self._client = httpx.AsyncClient(base_url=self.base, headers=headers, timeout=30.0)

    async def create_virtual_account(
        self,
        customer_name: str,
        bvn: str,
        mobile_number: str,
        *,
        email: str | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "customer_name": customer_name,
            "bvn": bvn,
            "mobile_number": mobile_number,
            "currency": "NGN",
        }
        if email:
            body["email"] = email.strip()
        try:
            r = await self._client.post("/virtual-account", json=body)
            r.raise_for_status()
            data = r.json()
            return {
                "virtual_account_number": data.get("virtual_account_number") or data.get("account_number"),
                "account_reference": data.get("account_reference") or data.get("reference"),
                "raw": data,
            }
        except Exception as e:
            logger.exception("create_virtual_account failed: %s", e)
            raise

    async def get_transaction_details(self, transaction_ref: str) -> dict[str, Any]:
        encoded = quote(str(transaction_ref).strip(), safe="")
        try:
            r = await self._client.get(f"/transaction/verify/{encoded}")
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            body_preview = (e.response.text or "")[:400]
            logger.warning(
                "get_transaction_details HTTP %s ref=%r body_preview=%s",
                e.response.status_code,
                transaction_ref,
                body_preview,
            )
            raise
        except Exception as e:
            logger.exception("get_transaction_details failed: %s", e)
            raise

    async def payout_account_lookup(self, bank_code: str, account_number: str) -> dict[str, Any]:
        """Squad Transfer API — resolve recipient account name before ``payout/transfer``."""
        body = {"bank_code": bank_code.strip(), "account_number": account_number.strip()}
        try:
            r = await self._client.post("/payout/account/lookup", json=body)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            logger.warning(
                "payout_account_lookup HTTP %s body_preview=%s",
                e.response.status_code,
                (e.response.text or "")[:400],
            )
            raise
        except Exception as e:
            logger.exception("payout_account_lookup failed: %s", e)
            raise

    async def initiate_transfer(
        self,
        amount: int,
        bank_code: str,
        account_number: str,
        account_name: str,
        reference: str,
        narration: str,
    ) -> dict[str, Any]:
        if not settings["SQUAD_ENABLE_PAYOUT"]:
            logger.warning("initiate_transfer blocked: SQUAD_ENABLE_PAYOUT is false")
            return {"success": False, "error": "SQUAD_ENABLE_PAYOUT is disabled"}
        # Squad Fund Transfer expects documented field names (not legacy aliases).
        body = {
            "transaction_reference": reference.strip(),
            "amount": str(int(amount)),
            "bank_code": bank_code.strip(),
            "account_number": account_number.strip(),
            "account_name": account_name.strip(),
            "currency_id": "NGN",
            "remark": (narration.strip() or reference.strip())[:512],
        }
        try:
            r = await self._client.post("/payout/transfer", json=body)
            ok = r.status_code < 400
            data = r.json() if r.content else {}
            logger.info("initiate_transfer status=%s body=%s", r.status_code, data)
            return {"success": ok, "status_code": r.status_code, "data": data}
        except Exception as e:
            logger.exception("initiate_transfer failed: %s", e)
            return {"success": False, "error": str(e)}

    async def initiate_inline_checkout(
        self,
        *,
        email: str,
        amount_kobo: int,
        transaction_ref: str,
        customer_name: str | None = None,
        callback_url: str | None = None,
        payment_channels: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Squad Payments — initiate inline checkout. Docs: POST ``/transaction/initiate``.
        Returns Squad JSON plus ``checkout_url`` when derivable from the payload.
        """
        body: dict[str, Any] = {
            "amount": int(amount_kobo),
            "email": email.strip(),
            "currency": "NGN",
            "initiate_type": "inline",
            "transaction_ref": transaction_ref.strip(),
            "metadata": {"purpose": "titan_support", "product": "Titan fraud ops demo"},
        }
        if customer_name:
            body["customer_name"] = customer_name.strip()[:200]
        if callback_url:
            body["callback_url"] = callback_url.strip()
        if payment_channels:
            body["payment_channels"] = payment_channels
        try:
            r = await self._client.post("/transaction/initiate", json=body)
            r.raise_for_status()
            raw = r.json()
        except httpx.HTTPStatusError as e:
            logger.warning(
                "initiate_inline_checkout HTTP %s body_preview=%s",
                e.response.status_code,
                (e.response.text or "")[:400],
            )
            raise
        except Exception as e:
            logger.exception("initiate_inline_checkout failed: %s", e)
            raise

        checkout = _extract_squad_checkout_url(raw)
        out = dict(raw) if isinstance(raw, dict) else {"raw": raw}
        if checkout:
            out["checkout_url"] = checkout
        return out

    async def hold_transaction(self, transaction_ref: str, reason: str) -> dict[str, Any]:
        db = SessionLocal()
        try:
            tx = db.query(Transaction).filter_by(transaction_ref=transaction_ref).first()
            if tx is None:
                return {"ok": False, "error": "transaction not found"}
            tx.status = "held"
            db.add(
                AuditLog(
                    event_type="hold_placed",
                    transaction_ref=transaction_ref,
                    details=json.dumps({"reason": reason}),
                    performed_by="system",
                )
            )
            db.commit()
            return {"ok": True, "transaction_ref": transaction_ref, "status": "held", "reason": reason}
        except Exception as e:
            logger.exception("hold_transaction failed: %s", e)
            db.rollback()
            return {"ok": False, "error": str(e)}
        finally:
            db.close()


squad_client = SquadClient()
