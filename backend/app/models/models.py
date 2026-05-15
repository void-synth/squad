"""SQLAlchemy ORM models for Titan."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_ref: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    amount: Mapped[float] = mapped_column(Float)  # kobo
    sender_account: Mapped[str] = mapped_column(String(64))
    receiver_account: Mapped[str] = mapped_column(String(64))
    sender_bank: Mapped[str] = mapped_column(String(128))
    receiver_bank: Mapped[str] = mapped_column(String(128))
    sender_name: Mapped[str] = mapped_column(String(128), default="")
    receiver_name: Mapped[str] = mapped_column(String(128), default="")
    description: Mapped[str] = mapped_column(String(512), default="")
    device_id: Mapped[str] = mapped_column(String(128), default="")
    bvn: Mapped[str] = mapped_column(String(32), default="")
    # pending: received, not yet scored; safe/flagged/held from AI; released/escalated from analysts
    status: Mapped[str] = mapped_column(String(32), default="pending")
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    fraud_alerts: Mapped[list["FraudAlert"]] = relationship("FraudAlert", back_populates="transaction")


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    risk_score: Mapped[float] = mapped_column(Float)
    alert_level: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text)
    pattern_type: Mapped[str] = mapped_column(String(64))
    action_taken: Mapped[str] = mapped_column(String(32), default="held")
    resolved_by: Mapped[str] = mapped_column(String(128), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transaction: Mapped["Transaction"] = relationship("Transaction", back_populates="fraud_alerts")


class AccountProfile(Base):
    __tablename__ = "account_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    bank_name: Mapped[str] = mapped_column(String(128))
    bvn: Mapped[str] = mapped_column(String(32), default="")
    avg_transaction_amount: Mapped[float] = mapped_column(Float, default=0.0)
    avg_daily_transactions: Mapped[float] = mapped_column(Float, default=0.0)
    is_blacklisted: Mapped[bool] = mapped_column(Boolean, default=False)
    blacklist_reason: Mapped[str] = mapped_column(String(512), default="")
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    transaction_ref: Mapped[str] = mapped_column(String(255), default="")
    details: Mapped[str] = mapped_column(Text)
    performed_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
