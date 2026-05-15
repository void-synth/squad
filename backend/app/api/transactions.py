"""REST endpoints for dashboard: transactions, alerts, stats, analyst actions."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Annotated, Any

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.ai.graph_engine import transaction_graph
from app.core.config import settings
from app.core.database import get_db
from app.core.socket_manager import broadcast_alert, broadcast_stats
from app.models.models import AuditLog, FraudAlert, Transaction
from app.services.platform_fee import settlement_breakdown_gross_kobo, summary_fee_fields
from app.services.stats import dashboard_stats
from app.services.squad_client import squad_client

router = APIRouter(prefix="/api/v1", tags=["transactions"])

logger = logging.getLogger(__name__)


def _tx_to_summary(tx: Transaction) -> dict[str, Any]:
    gross = float(tx.amount or 0)
    row: dict[str, Any] = {
        "id": tx.id,
        "transaction_ref": tx.transaction_ref,
        "amount_naira": gross / 100.0,
        "sender_account": tx.sender_account,
        "receiver_account": tx.receiver_account,
        "sender_bank": tx.sender_bank,
        "receiver_bank": tx.receiver_bank,
        "sender_name": tx.sender_name or "",
        "receiver_name": tx.receiver_name or "",
        "description": (tx.description or "")[:512],
        "status": tx.status,
        "risk_score": float(tx.risk_score or 0),
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
    }
    row.update(summary_fee_fields(gross))
    return row


@router.get("/transactions")
def list_transactions(
    db: Annotated[Session, Depends(get_db)],
    tx_status: str | None = Query(None, alias="status"),
):
    q = db.query(Transaction).order_by(Transaction.created_at.desc())
    if tx_status:
        q = q.filter(Transaction.status == tx_status)
    rows = q.limit(300).all()
    return [_tx_to_summary(t) for t in rows]


@router.get("/transactions/{transaction_ref}")
async def get_transaction(transaction_ref: str, db: Annotated[Session, Depends(get_db)]):
    tx = db.query(Transaction).filter_by(transaction_ref=transaction_ref).first()
    if tx is None:
        raise HTTPException(status_code=404, detail="Not found")
    alert = (
        db.query(FraudAlert)
        .filter(FraudAlert.transaction_id == tx.id)
        .order_by(FraudAlert.id.desc())
        .first()
    )
    graph_data = transaction_graph.get_graph_data(tx.sender_account)
    gross_kobo = float(tx.amount or 0)
    out: dict[str, Any] = {
        "transaction": _tx_to_summary(tx),
        "settlement": settlement_breakdown_gross_kobo(gross_kobo),
        "fraud_alert": None,
        "graph_data": graph_data,
        "squad": None,
    }
    if alert:
        out["fraud_alert"] = {
            "id": alert.id,
            "risk_score": float(alert.risk_score),
            "alert_level": alert.alert_level,
            "reason": alert.reason,
            "pattern_type": alert.pattern_type,
            "action_taken": alert.action_taken,
            "resolved_by": alert.resolved_by,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
        }
    if settings["SQUAD_SECRET_KEY"]:
        try:
            out["squad"] = await squad_client.get_transaction_details(transaction_ref)
        except Exception as e:
            logger.warning("Squad verify failed for %s: %s", transaction_ref, e)
    return out


@router.get("/alerts")
def list_alerts(
    db: Annotated[Session, Depends(get_db)],
    resolved: bool | None = Query(None),
):
    q = (
        db.query(FraudAlert)
        .options(joinedload(FraudAlert.transaction))
        .filter(FraudAlert.alert_level >= 2)
        .order_by(FraudAlert.created_at.desc())
    )
    if resolved is False:
        q = q.filter(FraudAlert.resolved_at.is_(None))
    rows = q.all()
    out = []
    for a in rows:
        t = a.transaction
        out.append(
            {
                "id": a.id,
                "risk_score": float(a.risk_score),
                "alert_level": a.alert_level,
                "reason": a.reason,
                "pattern_type": a.pattern_type,
                "action_taken": a.action_taken,
                "resolved_by": a.resolved_by,
                "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
                "transaction": _tx_to_summary(t) if t else None,
            }
        )
    return out


class AnalystActionBody(BaseModel):
    analyst_name: str
    release_reason: str = ""


@router.post("/alerts/{alert_id}/release")
async def release_alert(alert_id: int, body: AnalystActionBody, db: Annotated[Session, Depends(get_db)]):
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    tx = db.get(Transaction, alert.transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    now = datetime.now(timezone.utc)
    alert.action_taken = "released"
    alert.resolved_by = body.analyst_name
    alert.resolved_at = now
    tx.status = "released"

    db.add(
        AuditLog(
            event_type="hold_released",
            transaction_ref=tx.transaction_ref,
            details=json.dumps({"analyst": body.analyst_name, "reason": body.release_reason}),
            performed_by=body.analyst_name,
        )
    )
    db.commit()
    db.refresh(alert)

    await broadcast_alert(
        {
            "alert_id": alert.id,
            "transaction_ref": tx.transaction_ref,
            "risk_score": float(alert.risk_score),
            "alert_level": alert.alert_level,
            "reason": alert.reason,
            "pattern_type": alert.pattern_type,
            "action_taken": alert.action_taken,
            "resolved_by": alert.resolved_by,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "sender_account": tx.sender_account,
            "sender_bank": tx.sender_bank,
            "receiver_account": tx.receiver_account,
            "receiver_bank": tx.receiver_bank,
            "amount_naira": float(tx.amount) / 100.0,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "transaction": _tx_to_summary(tx),
        }
    )
    stats = dashboard_stats(db)
    await broadcast_stats(stats)

    return {
        "id": alert.id,
        "action_taken": alert.action_taken,
        "resolved_by": alert.resolved_by,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "transaction": _tx_to_summary(tx),
    }


@router.post("/alerts/{alert_id}/escalate")
async def escalate_alert(alert_id: int, body: AnalystActionBody, db: Annotated[Session, Depends(get_db)]):
    alert = db.get(FraudAlert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    tx = db.get(Transaction, alert.transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    now = datetime.now(timezone.utc)
    alert.action_taken = "escalated"
    alert.resolved_by = body.analyst_name
    alert.resolved_at = now
    tx.status = "escalated"

    db.add(
        AuditLog(
            event_type="hold_escalated",
            transaction_ref=tx.transaction_ref,
            details=json.dumps({"analyst": body.analyst_name, "reason": body.release_reason}),
            performed_by=body.analyst_name,
        )
    )
    db.commit()
    db.refresh(alert)

    await broadcast_alert(
        {
            "alert_id": alert.id,
            "transaction_ref": tx.transaction_ref,
            "risk_score": float(alert.risk_score),
            "alert_level": alert.alert_level,
            "reason": alert.reason,
            "pattern_type": alert.pattern_type,
            "action_taken": alert.action_taken,
            "resolved_by": alert.resolved_by,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
            "sender_account": tx.sender_account,
            "sender_bank": tx.sender_bank,
            "receiver_account": tx.receiver_account,
            "receiver_bank": tx.receiver_bank,
            "amount_naira": float(tx.amount) / 100.0,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "transaction": _tx_to_summary(tx),
        }
    )
    stats = dashboard_stats(db)
    await broadcast_stats(stats)

    return {
        "id": alert.id,
        "action_taken": alert.action_taken,
        "resolved_by": alert.resolved_by,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        "transaction": _tx_to_summary(tx),
    }


@router.get("/stats")
def get_stats(db: Annotated[Session, Depends(get_db)]):
    return dashboard_stats(db)
