"""Squad webhook receiver: HMAC verification and queue ingest."""

import hashlib
import hmac
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core import queue as redis_queue
from app.models.models import Transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["webhook"])


def _verify_signature(raw_body: bytes, signature_header: str | None) -> bool:
    secret = settings["SQUAD_SECRET_KEY"]
    if not secret or not signature_header:
        return False
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature_header.strip())


@router.post("/webhook/squad")
async def squad_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    x_squad_signature: Annotated[str | None, Header(alias="x-squad-signature")] = None,
):
    """
    Receive Squad webhooks. Verifies HMAC-SHA256 of raw body vs x-squad-signature (hex).
    """
    raw_body = await request.body()

    if not _verify_signature(raw_body, x_squad_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "Invalid signature"})

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Invalid JSON body: %s", e)
        raise HTTPException(status_code=400, detail={"error": "Invalid JSON"}) from e

    def g(key: str, default: str = "") -> str:
        v = payload.get(key, default)
        if v is None:
            return default
        return str(v)

    transaction_ref = g("transaction_ref")
    if not transaction_ref:
        raise HTTPException(status_code=400, detail={"error": "transaction_ref required"})

    amount = float(payload.get("amount", 0) or 0)

    tx = Transaction(
        transaction_ref=transaction_ref,
        amount=amount,
        sender_account=g("sender_account"),
        receiver_account=g("receiver_account"),
        sender_bank=g("sender_bank"),
        receiver_bank=g("receiver_bank"),
        description=g("description", ""),
        device_id=g("device_id", ""),
        bvn=g("bvn", ""),
        status="pending",
        risk_score=0.0,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    queue_payload = {
        "id": tx.id,
        "transaction_ref": tx.transaction_ref,
        "amount": tx.amount,
        "sender_account": tx.sender_account,
        "receiver_account": tx.receiver_account,
        "sender_bank": tx.sender_bank,
        "receiver_bank": tx.receiver_bank,
        "description": tx.description,
        "device_id": tx.device_id,
        "bvn": tx.bvn,
        "receiver_is_new": bool(payload.get("receiver_is_new", False)),
    }
    await redis_queue.push_transaction(queue_payload)

    return {"status": "received"}


@router.get("/webhook/test")
async def webhook_test_queue():
    length = await redis_queue.get_queue_length()
    return {"queue_length": length}
