"""Squad webhook receiver: signature verification and queue ingest."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core import queue as redis_queue
from app.models.models import Transaction
from app.services.squad_webhook_normalize import normalize_squad_webhook_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["webhook"])


def _verify_squad_webhook(raw_body: bytes, x_encrypted_body: str | None, x_legacy_sig: str | None) -> bool:
    """
    Official Squad: ``x-squad-encrypted-body`` = HMAC-SHA512(secret, raw_body), hex (case-insensitive).

    Must use the **raw request body bytes** (same as PHP ``php://input``). Docs sometimes show
    ``JSON.stringify(body)`` in Node—re-stringifying can break verification if spacing differs.

    Local ``simulate.py``: ``x-squad-signature`` = HMAC-SHA256(secret, raw_body), hex.

    If ``SQUAD_WEBHOOK_LEGACY_SHA256`` is false, legacy header is not accepted unless official header verifies.
    """
    secret = settings["SQUAD_SECRET_KEY"]
    if not secret:
        return False

    legacy_ok = bool(settings["SQUAD_WEBHOOK_LEGACY_SHA256"])

    if x_encrypted_body:
        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha512).hexdigest().upper()
        expected = x_encrypted_body.strip().upper()
        return hmac.compare_digest(digest, expected)

    if legacy_ok and x_legacy_sig:
        digest256 = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(digest256, x_legacy_sig.strip())

    return False


@router.post("/webhook/squad")
async def squad_webhook(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    """
    Receive Squad webhooks.

    Verifies ``x-squad-encrypted-body`` (HMAC-SHA512) per Squad docs, or legacy ``x-squad-signature`` (SHA256)
    for local ``simulate.py`` when ``SQUAD_WEBHOOK_LEGACY_SHA256`` is enabled.
    """
    raw_body = await request.body()

    enc = request.headers.get("x-squad-encrypted-body") or request.headers.get("X-Squad-Encrypted-Body")
    legacy = request.headers.get("x-squad-signature") or request.headers.get("X-Squad-Signature")

    if not _verify_squad_webhook(raw_body, enc, legacy):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail={"error": "Invalid signature"})

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.warning("Invalid JSON body: %s", e)
        raise HTTPException(status_code=400, detail={"error": "Invalid JSON"}) from e

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail={"error": "JSON object required"})

    flat = normalize_squad_webhook_payload(payload)
    if not flat or not flat.get("transaction_ref"):
        raise HTTPException(status_code=400, detail={"error": "transaction_ref required"})

    def g(key: str, default: str = "") -> str:
        v = flat.get(key, default)
        if v is None:
            return default
        return str(v)

    transaction_ref = g("transaction_ref")
    amount = float(flat.get("amount", 0) or 0)

    tx = Transaction(
        transaction_ref=transaction_ref,
        amount=amount,
        sender_account=g("sender_account"),
        receiver_account=g("receiver_account"),
        sender_bank=g("sender_bank"),
        receiver_bank=g("receiver_bank"),
        sender_name=g("sender_name", ""),
        receiver_name=g("receiver_name", ""),
        description=g("description", ""),
        device_id=g("device_id", ""),
        bvn=g("bvn", ""),
        status="pending",
        risk_score=0.0,
    )
    db.add(tx)
    try:
        db.commit()
        db.refresh(tx)
    except IntegrityError:
        db.rollback()
        logger.info("Duplicate webhook for transaction_ref=%s — acknowledged", transaction_ref)
        return {"status": "duplicate"}

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
        "sender_name": tx.sender_name,
        "receiver_name": tx.receiver_name,
        "receiver_is_new": bool(flat.get("receiver_is_new", False)),
    }
    await redis_queue.push_transaction(queue_payload)

    return {"status": "received"}


@router.get("/webhook/test")
async def webhook_test_queue():
    length = await redis_queue.get_queue_length()
    return {"queue_length": length}
