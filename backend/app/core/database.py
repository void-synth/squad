"""Database engine, session factory, and FastAPI dependency."""

from collections.abc import Generator

import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.models import Base

logger = logging.getLogger(__name__)

DATABASE_URL = settings["DATABASE_URL"] or "sqlite:///./squad_sentinel_local.db"

_engine_kwargs: dict = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _migrate_transaction_name_columns() -> None:
    insp = inspect(engine)
    if "transactions" not in insp.get_table_names():
        return
    existing = {c["name"] for c in insp.get_columns("transactions")}
    alters: list[str] = []
    col_type = "TEXT" if DATABASE_URL.startswith("sqlite") else "VARCHAR(128)"
    pending: list[str] = []
    if "sender_name" not in existing:
        pending.append("sender_name")
    if "receiver_name" not in existing:
        pending.append("receiver_name")
    if not pending:
        return
    # SQLite allows only one ADD COLUMN per ALTER TABLE (Postgres allows comma-separated).
    with engine.begin() as conn:
        for col in pending:
            ddl = f"ALTER TABLE transactions ADD COLUMN {col} {col_type} DEFAULT ''"
            conn.execute(text(ddl))
            logger.info("Migrated transactions: %s", ddl)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _migrate_transaction_name_columns()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
