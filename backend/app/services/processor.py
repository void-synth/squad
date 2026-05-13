"""
Background worker: Redis queue -> risk engine -> DB -> Socket.IO.

We process asynchronously so the webhook can return immediately; heavy ML
and DB work must not block payment ingestion or risk timeouts during spikes.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.risk_engine import risk_engine
from app.core import queue as redis_queue
from app.core.database import SessionLocal
from app.core.socket_manager import broadcast_alert, broadcast_stats, broadcast_transaction
from app.models.models import AccountProfile, AuditLog, FraudAlert, Transaction
from app.services.stats import dashboard_stats

logger = logging.getLogger(__name__)

_processed_since_stats = 0
_total_processed = 0


async def process_transaction(transaction: dict) -> None:
    global _processed_since_stats, _total_processed
    db: Session = SessionLocal()
    try:
        tx_id = int(transaction["id"])
        tx = db.get(Transaction, tx_id)
        if tx is None:
            logger.warning("Transaction id=%s not found", tx_id)
            return

        prof = db.query(AccountProfile).filter_by(account_number=tx.sender_account).first()
        profile_dict = None
        if prof:
            profile_dict = {
                "avg_transaction_amount": float(prof.avg_transaction_amount or 0),
                "avg_daily_transactions": float(prof.avg_daily_transactions or 0),
            }

        payload = {
            "id": tx.id,
            "transaction_ref": tx.transaction_ref,
            "amount": float(tx.amount),
            "sender_account": tx.sender_account,
            "receiver_account": tx.receiver_account,
            "sender_bank": tx.sender_bank,
            "receiver_bank": tx.receiver_bank,
            "description": tx.description or "",
            "device_id": tx.device_id or "",
            "bvn": tx.bvn or "",
            "receiver_is_new": bool(transaction.get("receiver_is_new", False)),
        }

        result = risk_engine.analyse(payload, profile_dict)

        tx.risk_score = float(result["final_score"])
        level = int(result["alert_level"])
        if level == 0:
            tx.status = "safe"
        elif level == 2:
            tx.status = "flagged"
        else:
            tx.status = "held"

        if level in (2, 3):
            alert = FraudAlert(
                transaction_id=tx.id,
                risk_score=float(result["final_score"]),
                alert_level=level,
                reason=result["reason"],
                pattern_type=result["pattern_type"],
                action_taken="monitored" if level == 2 else "held",
            )
            db.add(alert)
            db.flush()

        event_type = "fraud_detected" if level in (2, 3) else "transaction_scored"
        db.add(
            AuditLog(
                event_type=event_type,
                transaction_ref=tx.transaction_ref,
                details=json.dumps(
                    {
                        "final_score": result["final_score"],
                        "alert_level": level,
                        "pattern_type": result["pattern_type"],
                        "recommended_action": result["recommended_action"],
                    }
                ),
                performed_by="system",
            )
        )

        # Account profile upsert (sender)
        now = datetime.now(timezone.utc)
        if prof is None:
            prof = AccountProfile(
                account_number=tx.sender_account,
                bank_name=tx.sender_bank,
                bvn=tx.bvn or "",
                avg_transaction_amount=float(tx.amount),
                avg_daily_transactions=1.0,
                first_seen=now,
                last_seen=now,
            )
            db.add(prof)
        else:
            a = float(prof.avg_transaction_amount or 0)
            prof.avg_transaction_amount = 0.9 * a + 0.1 * float(tx.amount) if a > 0 else float(tx.amount)
            prof.avg_daily_transactions = min(float(prof.avg_daily_transactions or 0) + 0.05, 100.0)
            prof.last_seen = now
            prof.bank_name = tx.sender_bank or prof.bank_name

        db.commit()
        db.refresh(tx)

        summary = {
            "id": tx.id,
            "transaction_ref": tx.transaction_ref,
            "amount": float(tx.amount),
            "amount_naira": float(tx.amount) / 100.0,
            "sender_account": tx.sender_account,
            "receiver_account": tx.receiver_account,
            "sender_bank": tx.sender_bank,
            "receiver_bank": tx.receiver_bank,
            "status": tx.status,
            "risk_score": float(tx.risk_score),
            "created_at": tx.created_at.isoformat() if tx.created_at else None,
        }
        await broadcast_transaction(summary)

        if level == 3:
            alert_row = (
                db.query(FraudAlert)
                .filter(FraudAlert.transaction_id == tx.id)
                .order_by(FraudAlert.id.desc())
                .first()
            )
            if alert_row:
                await broadcast_alert(
                    {
                        "alert_id": alert_row.id,
                        "transaction_ref": tx.transaction_ref,
                        "risk_score": float(alert_row.risk_score),
                        "alert_level": alert_row.alert_level,
                        "reason": alert_row.reason,
                        "pattern_type": alert_row.pattern_type,
                        "action_taken": alert_row.action_taken,
                        "sender_account": tx.sender_account,
                        "sender_bank": tx.sender_bank,
                        "receiver_account": tx.receiver_account,
                        "receiver_bank": tx.receiver_bank,
                        "amount_naira": float(tx.amount) / 100.0,
                        "created_at": alert_row.created_at.isoformat() if alert_row.created_at else None,
                    }
                )

        _processed_since_stats += 1
        _total_processed += 1
        if _processed_since_stats >= 10:
            _processed_since_stats = 0
            stats = dashboard_stats(db)
            await broadcast_stats(stats)

    except Exception:
        logger.exception("process_transaction failed for %s", transaction)
        db.rollback()
    finally:
        db.close()


async def worker_loop() -> None:
    while True:
        item = await redis_queue.pop_transaction()
        if item:
            try:
                await process_transaction(item)
            except Exception:
                logger.exception("worker_loop iteration failed")
        else:
            await asyncio.sleep(0.1)


_worker_task: asyncio.Task | None = None


def start_worker_background() -> asyncio.Task:
    global _worker_task
    _worker_task = asyncio.create_task(worker_loop())
    return _worker_task


async def stop_worker_background() -> None:
    global _worker_task
    if _worker_task is not None:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass
        _worker_task = None
