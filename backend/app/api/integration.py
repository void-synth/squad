"""Non-auth operational endpoints: health checks and Squad HTTP proxies (server-side keys only)."""

from __future__ import annotations

import logging
from typing import Any

import redis as redis_sync
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.squad_client import squad_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["integration"])


@router.get("/health")
def health() -> dict[str, Any]:
    """Liveness + dependency checks for dashboards and load balancers."""
    db_ok = False
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        logger.debug("health: database check failed", exc_info=True)

    redis_ok = False
    try:
        r = redis_sync.from_url(settings["REDIS_URL"], decode_responses=True)
        r.ping()
        redis_ok = True
    except Exception:
        logger.debug("health: redis check failed", exc_info=True)

    overall = "ok" if db_ok and redis_ok else "degraded"
    return {"status": overall, "database": db_ok, "redis": redis_ok}


@router.get("/integration/squad/status")
def squad_integration_status() -> dict[str, Any]:
    """Whether Squad credentials and payout gate are configured (no secrets returned)."""
    return {
        "secret_configured": bool(settings["SQUAD_SECRET_KEY"]),
        "public_configured": bool(settings["SQUAD_PUBLIC_KEY"]),
        "payout_enabled": bool(settings["SQUAD_ENABLE_PAYOUT"]),
        "base_url": settings["SQUAD_BASE_URL"],
    }


@router.get("/integration/squad/verify/{transaction_ref}")
async def squad_verify_transaction(transaction_ref: str) -> dict[str, Any]:
    """Proxy to Squad payment verify (same payload as Squad API)."""
    if not settings["SQUAD_SECRET_KEY"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Squad secret key is not configured",
        )
    try:
        return await squad_client.get_transaction_details(transaction_ref)
    except Exception as e:
        logger.warning("Squad verify proxy failed for %s: %s", transaction_ref, e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Squad verify request failed",
        ) from e


class VirtualAccountBody(BaseModel):
    customer_name: str = Field(..., min_length=1)
    bvn: str = Field(..., min_length=1)
    mobile_number: str = Field(..., min_length=1)


@router.post("/integration/squad/virtual-account")
async def squad_create_virtual_account(body: VirtualAccountBody) -> dict[str, Any]:
    """Proxy to Squad virtual account creation (sandbox/production per SQUAD_BASE_URL)."""
    if not settings["SQUAD_SECRET_KEY"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Squad secret key is not configured",
        )
    try:
        return await squad_client.create_virtual_account(
            customer_name=body.customer_name,
            bvn=body.bvn,
            mobile_number=body.mobile_number,
        )
    except Exception as e:
        logger.warning("Squad virtual-account proxy failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Squad virtual account request failed",
        ) from e


class PayoutBody(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in kobo")
    bank_code: str = Field(..., min_length=1)
    account_number: str = Field(..., min_length=1)
    reference: str = Field(..., min_length=1)
    narration: str = ""


@router.post("/integration/squad/payout")
async def squad_payout(body: PayoutBody) -> dict[str, Any]:
    """
    Proxy to Squad payout transfer. Blocked unless ``SQUAD_ENABLE_PAYOUT`` is true
    (same behaviour as ``SquadClient.initiate_transfer``).
    """
    if not settings["SQUAD_SECRET_KEY"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Squad secret key is not configured",
        )
    return await squad_client.initiate_transfer(
        amount=body.amount,
        bank_code=body.bank_code,
        account_number=body.account_number,
        reference=body.reference,
        narration=body.narration or "Titan payout",
    )


@router.get("/integration/queue")
async def integration_queue_length() -> dict[str, Any]:
    """Redis transaction queue depth (same metric as webhook test)."""
    from app.core import queue as redis_queue

    length = await redis_queue.get_queue_length()
    return {"queue_length": length}
