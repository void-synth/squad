"""
HTTP client for Squad sandbox APIs.

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

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.models import AuditLog, Transaction

logger = logging.getLogger(__name__)


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

    async def create_virtual_account(self, customer_name: str, bvn: str, mobile_number: str) -> dict[str, Any]:
        body = {
            "customer_name": customer_name,
            "bvn": bvn,
            "mobile_number": mobile_number,
            "currency": "NGN",
        }
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
        try:
            r = await self._client.get(f"/transaction/verify/{transaction_ref}")
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.exception("get_transaction_details failed: %s", e)
            raise

    async def initiate_transfer(
        self,
        amount: int,
        bank_code: str,
        account_number: str,
        reference: str,
        narration: str,
    ) -> dict[str, Any]:
        body = {
            "amount": amount,
            "bank_code": bank_code,
            "account_number": account_number,
            "reference": reference,
            "narration": narration,
            "currency": "NGN",
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
