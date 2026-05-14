"""Dashboard stats aggregation (shared by API and worker)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import FraudAlert, Transaction


def dashboard_stats(db: Session) -> dict:
    total_transactions = int(db.scalar(select(func.count()).select_from(Transaction)) or 0)
    total_flagged = int(
        db.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.status.in_(["flagged", "held"]))
        )
        or 0
    )
    total_held = int(
        db.scalar(select(func.count()).select_from(Transaction).where(Transaction.status == "held")) or 0
    )
    total_released = int(
        db.scalar(select(func.count()).select_from(Transaction).where(Transaction.status == "released")) or 0
    )

    held_sum_kobo = db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0.0))
        .select_from(Transaction)
        .where(Transaction.status == "held")
    )
    total_naira_intercepted = float(held_sum_kobo or 0) / 100.0

    false_positive_rate = (total_released / total_held * 100.0) if total_held > 0 else 0.0

    subq = (
        select(Transaction.sender_account, func.count(FraudAlert.id).label("cnt"))
        .join(FraudAlert, FraudAlert.transaction_id == Transaction.id)
        .where(FraudAlert.alert_level >= 2)
        .group_by(Transaction.sender_account)
        .order_by(func.count(FraudAlert.id).desc())
        .limit(5)
    )
    rows = db.execute(subq).all()
    top_flagged_accounts = [{"sender_account": r[0], "flags": int(r[1])} for r in rows]

    rate = float(settings["TITAN_PLATFORM_FEE_RATE"])
    fee_sum_kobo = db.scalar(
        select(func.coalesce(func.sum(func.round(Transaction.amount * rate)), 0.0)).select_from(Transaction)
    )
    fee_sum_kobo = float(fee_sum_kobo or 0.0)
    gross_all_kobo = float(
        db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0.0)).select_from(Transaction)) or 0.0
    )
    net_sum_kobo = gross_all_kobo - fee_sum_kobo
    total_platform_fee_naira = fee_sum_kobo / 100.0
    total_net_settlement_naira = net_sum_kobo / 100.0

    return {
        "total_transactions": total_transactions,
        "total_flagged": total_flagged,
        "total_held": total_held,
        "total_released": total_released,
        "total_naira_intercepted": total_naira_intercepted,
        "false_positive_rate": round(false_positive_rate, 2),
        "top_flagged_accounts": top_flagged_accounts,
        "platform_fee_rate": rate,
        "total_platform_fee_naira": round(total_platform_fee_naira, 2),
        "total_net_settlement_naira": round(total_net_settlement_naira, 2),
        "platform_fee_receiver_account": settings["TITAN_FEE_RECEIVER_ACCOUNT"],
    }
