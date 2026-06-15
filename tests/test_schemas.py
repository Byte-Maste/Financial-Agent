from datetime import date
from schemas.models import Transaction


def test_transaction_default_category():
    txn = Transaction(
        transaction_id="abc123",
        user_id="user-1",
        transaction_date=date(2024, 1, 15),
        amount=500.0,
        merchant="Netflix",
        raw_merchant="NETFLIX COM",
    )
    assert txn.category == "Uncategorized"
    assert txn.payment_mode == "UPI"


def test_transaction_validates_positive_amount():
    import pydantic
    try:
        Transaction(
            transaction_id="abc",
            user_id="u1",
            transaction_date=date.today(),
            amount=-100,
            merchant="Test",
            raw_merchant="test",
        )
        assert False, "Should have raised"
    except pydantic.ValidationError:
        pass


def test_routing_contract():
    from schemas.routing import OrchestratorRoutingContract
    route = OrchestratorRoutingContract(
        action="ingest",
        reasoning="User wants to upload a file",
        agent_payload={"file_type": "pdf"},
    )
    assert route.action == "ingest"
