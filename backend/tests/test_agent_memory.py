"""Agent memory index: name links and query resolution."""

from app.ai.agent.memory_index import build_memory, normalize_name, resolve_query_context
from app.models.models import Transaction


def test_normalize_name():
    assert normalize_name("Bolu Adeyemi") == "bolu adeyemi"
    assert normalize_name("  Daniel Okoro ") == "daniel okoro"


def test_memory_links_bolu_daniel_shared_opay(db_session) -> None:
    opay_acct = "9031112223"
    t1 = Transaction(
        transaction_ref="sqd_test_bolu_01",
        amount=500_000.0,
        sender_account="8011223344",
        receiver_account=opay_acct,
        sender_bank="UBA",
        receiver_bank="OPay",
        sender_name="Bolu Adeyemi",
        description="rent",
        status="safe",
    )
    t2 = Transaction(
        transaction_ref="sqd_test_daniel_01",
        amount=600_000.0,
        sender_account="8022334455",
        receiver_account=opay_acct,
        sender_bank="Access Bank",
        receiver_bank="OPay",
        sender_name="Daniel Okoro",
        description="fees",
        status="flagged",
    )
    db_session.add_all([t1, t2])
    db_session.commit()

    memory = build_memory(db_session)
    shared = [l for l in memory["links"] if l["type"] == "shared_receiver"]
    assert len(shared) >= 1
    refs = shared[0].get("transaction_refs", [])
    assert "sqd_test_bolu_01" in refs and "sqd_test_daniel_01" in refs

    ctx = resolve_query_context(memory, "link between bolu and daniel opay")
    assert len(ctx["transactions"]) >= 2
