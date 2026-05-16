"""Non-auth operational endpoints: health checks and Squad HTTP proxies (server-side keys only)."""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.squad_client import squad_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["integration"])

_CHECKOUT_CALLBACK_PATTERN = re.compile(
    r"^https://[^\s]+$|^http://localhost(:\d+)?(/[^\s]*)?$|^http://127\.0\.0\.1(:\d+)?(/[^\s]*)?$",
    re.IGNORECASE,
)


def _sanitize_checkout_callback(url: str | None) -> str | None:
    if url is None:
        return None
    u = str(url).strip()
    if len(u) < 8 or len(u) > 2048:
        return None
    if not _CHECKOUT_CALLBACK_PATTERN.match(u):
        return None
    return u


@router.get("/health")
async def health() -> dict[str, Any]:
    """Liveness + dependency checks for dashboards and load balancers."""
    db_ok = False
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        logger.debug("health: database check failed", exc_info=True)

    from app.core import queue as tx_queue

    queue_mode = await tx_queue.queue_backend()
    redis_ok = queue_mode == "redis"

    overall = "ok" if db_ok else "degraded"
    return {
        "status": overall,
        "database": db_ok,
        "redis": redis_ok,
        "queue": queue_mode,
    }


@router.get("/integration/squad/status")
def squad_integration_status() -> dict[str, Any]:
    """Whether Squad credentials and payout gate are configured (no secrets returned)."""
    return {
        "secret_configured": bool(settings["SQUAD_SECRET_KEY"]),
        "public_configured": bool(settings["SQUAD_PUBLIC_KEY"]),
        "payout_enabled": bool(settings["SQUAD_ENABLE_PAYOUT"]),
        "base_url": settings["SQUAD_BASE_URL"],
        "capabilities": {
            "webhook_sha512": True,
            "transaction_verify": True,
            "virtual_account_create": True,
            "payout_account_lookup": True,
            "payout_transfer": True,
            "checkout_inline": True,
            "checkout_return_probe": True,
        },
    }


class SquadCheckoutInitBody(BaseModel):
    email: str = Field(..., min_length=5, max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    amount_kobo: int = Field(..., gt=0, le=100_000_000, description="Amount in kobo (e.g. 10000 = ₦100)")
    customer_name: str | None = Field(None, max_length=200)
    callback_url: str | None = Field(
        None,
        max_length=2048,
        description="HTTPS or localhost URL Squad redirects to after payment (e.g. …/billing?squad_return=1).",
    )


@router.post("/integration/squad/checkout/initiate")
async def squad_checkout_initiate(body: SquadCheckoutInitBody) -> dict[str, Any]:
    """
    Start Squad **inline** checkout (Payments API). Returns ``checkout_url`` for browser redirect.
    Secret key stays server-side; amounts are capped for tip-jar style support payments.
    """
    if not settings["SQUAD_SECRET_KEY"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Squad secret key is not configured",
        )
    transaction_ref = f"TITAN_{uuid.uuid4().hex}"
    callback = _sanitize_checkout_callback(body.callback_url)
    try:
        payload = await squad_client.initiate_inline_checkout(
            email=body.email,
            amount_kobo=body.amount_kobo,
            transaction_ref=transaction_ref,
            customer_name=body.customer_name,
            callback_url=callback,
            payment_channels=["card", "bank", "ussd", "transfer"],
        )
    except Exception as e:
        logger.warning("Squad checkout initiate failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Squad checkout initiation failed",
        ) from e

    checkout_url = payload.get("checkout_url") if isinstance(payload, dict) else None
    if not checkout_url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Squad response did not include a checkout URL",
        )
    return {
        "transaction_ref": transaction_ref,
        "checkout_url": checkout_url,
        "squad": payload,
    }


@router.get("/integration/squad/checkout-return")
async def squad_checkout_return_probe(request: Request) -> dict[str, Any]:
    """
    Landing helper for Squad **redirect URL** configuration (payments modal / checkout).
    Returns echoed query params — wire your Squad dashboard redirect to this path in dev/staging.
    """
    return {
        "ok": True,
        "message": "Titan received Squad checkout redirect parameters.",
        "query_params": dict(request.query_params),
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
    email: str | None = Field(None, description="Optional — passed through when Squad expects customer email.")


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
            email=body.email,
        )
    except Exception as e:
        logger.warning("Squad virtual-account proxy failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Squad virtual account request failed",
        ) from e


class PayoutAccountLookupBody(BaseModel):
    bank_code: str = Field(..., min_length=1)
    account_number: str = Field(..., min_length=1)


@router.post("/integration/squad/payout/account-lookup")
async def squad_payout_account_lookup(body: PayoutAccountLookupBody) -> dict[str, Any]:
    """Proxy Squad ``POST /payout/account/lookup`` (recipient verification before transfer)."""
    if not settings["SQUAD_SECRET_KEY"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Squad secret key is not configured",
        )
    try:
        return await squad_client.payout_account_lookup(body.bank_code, body.account_number)
    except Exception as e:
        logger.warning("Squad payout account lookup failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Squad account lookup request failed",
        ) from e


class PayoutBody(BaseModel):
    amount: int = Field(..., gt=0, description="Amount in kobo")
    bank_code: str = Field(..., min_length=1)
    account_number: str = Field(..., min_length=1)
    account_name: str = Field(
        ...,
        min_length=1,
        description="Account holder name from Squad account lookup (required by Fund Transfer API).",
    )
    reference: str = Field(
        ...,
        min_length=1,
        description="Unique transaction_reference; Squad docs require merchant ID prefix.",
    )
    narration: str = Field("", description="Sent as Squad remark.")


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
        account_name=body.account_name,
        reference=body.reference,
        narration=body.narration or "Titan payout",
    )


@router.get("/integration/queue")
async def integration_queue_length() -> dict[str, Any]:
    """Redis transaction queue depth (same metric as webhook test)."""
    from app.core import queue as redis_queue

    length = await redis_queue.get_queue_length()
    return {"queue_length": length}
