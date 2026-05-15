"""Tests for demo workflow fixtures: webhook ingest, listing, stats, analyst release."""

from __future__ import annotations

import hashlib
import hmac
import json

from app.core.database import SessionLocal
from app.models.models import FraudAlert, Transaction


def _legacy_sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def test_demo_workflow_fixture_file_covers_pipeline(demo_fixture: dict) -> None:
    assert "simulation_config" in demo_fixture
    assert demo_fixture["simulation_config"]["num_events"] == 50
    assert "webhook" in demo_fixture
    assert demo_fixture["webhook"]["body"]["transaction_ref"]
    assert "queue_job" in demo_fixture
    assert "fraud_alert" in demo_fixture
    assert "live_feed_row" in demo_fixture
    assert "release" in demo_fixture
    assert "socket_io" in demo_fixture


def test_webhook_accepts_signed_payload(client, demo_fixture: dict) -> None:
    secret = "pytest_hmac_secret_for_webhook_tests_01"
    body_obj = dict(demo_fixture["webhook"]["body"])
    raw = json.dumps(body_obj, separators=(",", ":")).encode("utf-8")
    sig = _legacy_sign(secret, raw)

    res = client.post(
        "/api/v1/webhook/squad",
        content=raw,
        headers={"Content-Type": "application/json", "x-squad-signature": sig},
    )
    assert res.status_code == 200
    assert res.json() == {"status": "received"}

    listed = client.get("/api/v1/transactions").json()
    assert len(listed) == 1
    row = listed[0]
    assert row["transaction_ref"] == body_obj["transaction_ref"]
    assert row["status"] == "pending"
    assert row["amount_naira"] == body_obj["amount"] / 100.0


def test_webhook_rejects_bad_signature(client, demo_fixture: dict) -> None:
    body_obj = dict(demo_fixture["webhook"]["body"])
    body_obj["transaction_ref"] = "sqd_other_ref_xyz"
    raw = json.dumps(body_obj, separators=(",", ":")).encode("utf-8")

    res = client.post(
        "/api/v1/webhook/squad",
        content=raw,
        headers={"Content-Type": "application/json", "x-squad-signature": "deadbeef"},
    )
    assert res.status_code == 401


def test_stats_endpoint_returns_expected_keys(client) -> None:
    stats = client.get("/api/v1/stats").json()
    for key in (
        "total_transactions",
        "total_flagged",
        "total_held",
        "total_released",
        "total_naira_intercepted",
        "false_positive_rate",
        "top_flagged_accounts",
        "platform_fee_rate",
        "total_platform_fee_naira",
        "total_net_settlement_naira",
        "platform_fee_receiver_account",
    ):
        assert key in stats


def test_release_alert_updates_transaction_and_returns_summary(client) -> None:
    db = SessionLocal()
    try:
        tx = Transaction(
            transaction_ref="sqd_release_test_001",
            amount=500000.0,
            sender_account="1111222233",
            receiver_account="9031112223",
            sender_bank="GTBank",
            receiver_bank="OPay",
            description="fixture release",
            device_id="DEV_rel",
            bvn="22999887766",
            status="held",
            risk_score=0.91,
        )
        db.add(tx)
        db.flush()
        alert = FraudAlert(
            transaction_id=tx.id,
            risk_score=0.91,
            alert_level=3,
            reason="Test hold",
            pattern_type="test",
            action_taken="held",
        )
        db.add(alert)
        db.commit()
        alert_id = alert.id
    finally:
        db.close()

    res = client.post(
        f"/api/v1/alerts/{alert_id}/release",
        json={"analyst_name": "pytest_analyst", "release_reason": "OK to pay"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["action_taken"] == "released"
    assert data["resolved_by"] == "pytest_analyst"
    assert data["resolved_at"] is not None
    assert data["transaction"]["status"] == "released"
    assert data["transaction"]["transaction_ref"] == "sqd_release_test_001"

    db2 = SessionLocal()
    try:
        tx2 = db2.query(Transaction).filter_by(transaction_ref="sqd_release_test_001").one()
        assert tx2.status == "released"
        a2 = db2.get(FraudAlert, alert_id)
        assert a2 is not None
        assert a2.action_taken == "released"
        assert a2.resolved_by == "pytest_analyst"
        assert a2.resolved_at is not None
    finally:
        db2.close()


def test_list_alerts_includes_open_high_severity(client) -> None:
    db = SessionLocal()
    try:
        tx = Transaction(
            transaction_ref="sqd_alert_list_001",
            amount=100000.0,
            sender_account="2222333344",
            receiver_account="9042223334",
            sender_bank="UBA",
            receiver_bank="OPay",
            description="list test",
            device_id="DEV_l",
            bvn="",
            status="held",
            risk_score=0.8,
        )
        db.add(tx)
        db.flush()
        db.add(
            FraudAlert(
                transaction_id=tx.id,
                risk_score=0.8,
                alert_level=3,
                reason="High",
                pattern_type="velocity",
                action_taken="held",
            )
        )
        db.commit()
    finally:
        db.close()

    open_alerts = client.get("/api/v1/alerts", params={"resolved": "false"}).json()
    assert len(open_alerts) >= 1
    assert any(a["alert_level"] >= 2 and a["resolved_at"] is None for a in open_alerts)
