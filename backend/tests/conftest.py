"""Pytest setup: force test env before any app imports (dotenv does not override existing vars)."""

from __future__ import annotations

import json
import os
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _BACKEND_ROOT / ".pytest_titan.sqlite"

os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH.as_posix()}"
os.environ["SQUAD_SECRET_KEY"] = "pytest_hmac_secret_for_webhook_tests_01"
os.environ["SQUAD_WEBHOOK_LEGACY_SHA256"] = "true"
os.environ["TITAN_PLATFORM_FEE_RATE"] = "0.01"
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/15")

import pytest
from fastapi.testclient import TestClient

from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, init_db
from app.models.models import Base


@pytest.fixture(autouse=True)
def _reset_sqlite_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def demo_fixture() -> dict:
    path = _BACKEND_ROOT / "fixtures" / "demo_workflow.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def db_session() -> Session:
    init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> TestClient:
    from main import fastapi_app

    return TestClient(fastapi_app, raise_server_exceptions=True)
