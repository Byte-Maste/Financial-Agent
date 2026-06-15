import pytest


@pytest.fixture
def sample_csv_content() -> bytes:
    return b"date,amount,merchant,category,payment_mode\n2024-01-15,2500.00,Swiggy,Food,UPI\n2024-01-16,15000.00,Amazon,Shopping,Credit Card\n2024-01-17,500.00,Netflix,Subscriptions,Debit Card\n"


@pytest.fixture
def sample_upi_text() -> str:
    return "₹500.00 debited from UPI to Netflix on 2024-01-17"
