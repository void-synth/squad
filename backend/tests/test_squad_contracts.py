"""Contract-style tests against Squad doc shapes (signature, VA webhook JSON)."""

from __future__ import annotations

import hashlib
import hmac
import json

from app.services.squad_webhook_normalize import normalize_squad_webhook_payload


def _sha512(secret: str, raw: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha512).hexdigest().upper()


def test_webhook_accepts_official_x_squad_encrypted_body(client) -> None:
    secret = "pytest_hmac_secret_for_webhook_tests_01"
    body_obj = {
        "transaction_reference": "REFE52_DOC_SHAPE_PYTEST",
        "virtual_account_number": "2129125316",
        "principal_amount": "222.00",
        "settled_amount": "221.78",
        "fee_charged": "0.22",
        "customer_identifier": "SBN1EBZEQ8",
        "remarks": "Transfer FROM sandbox sandbox",
        "currency": "NGN",
        "channel": "virtual-account",
        "transaction_indicator": "C",
        "meta": {"freeze_transaction_ref": None, "reason_for_frozen_transaction": None},
    }
    raw = json.dumps(body_obj, separators=(",", ":")).encode("utf-8")
    sig = _sha512(secret, raw)

    res = client.post(
        "/api/v1/webhook/squad",
        content=raw,
        headers={"Content-Type": "application/json", "x-squad-encrypted-body": sig},
    )
    assert res.status_code == 200
    assert res.json().get("status") == "received"

    listed = client.get("/api/v1/transactions").json()
    assert len(listed) == 1
    assert listed[0]["transaction_ref"] == "REFE52_DOC_SHAPE_PYTEST"
    assert listed[0]["amount_naira"] == 222.0
    assert "indicator=C" in (listed[0].get("description") or "")


def test_normalize_va_nested_data_wrapper() -> None:
    payload = {
        "event": "charge.completed",
        "data": {
            "transaction_reference": "nested_REF_001",
            "principal_amount": "1500.50",
            "virtual_account_number": "9988776655",
            "customer_identifier": "CUST_ABC",
            "channel": "virtual-account",
            "remarks": "credit",
            "meta": {"freeze_transaction_ref": "FRZ_1", "reason_for_frozen_transaction": "review"},
        },
    }
    flat = normalize_squad_webhook_payload(payload)
    assert flat is not None
    assert flat["transaction_ref"] == "nested_REF_001"
    assert flat["amount"] == 150050.0
    assert "freeze_ref=FRZ_1" in flat["description"]


def test_transaction_verify_path_encodes_slashes() -> None:
    from urllib.parse import quote

    ref = "REFE52ARZHTS/1668421222619_1"
    encoded = quote(ref, safe="")
    assert "/" not in encoded
    assert "%2F" in encoded


def test_extract_squad_checkout_url_nested() -> None:
    from app.services.squad_client import _extract_squad_checkout_url

    assert (
        _extract_squad_checkout_url({"data": {"checkout_url": "https://checkout.example/pay"}})
        == "https://checkout.example/pay"
    )
    assert _extract_squad_checkout_url({"auth_url": "https://auth.example/a"}) == "https://auth.example/a"


def test_checkout_return_probe_echoes_query(client) -> None:
    res = client.get("/api/v1/integration/squad/checkout-return", params={"transaction_ref": "tr_x"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["query_params"]["transaction_ref"] == "tr_x"
