import io
from datetime import date

from services.parsing_service import parse_csv, _generate_transaction_id


def test_generate_transaction_id():
    tid = _generate_transaction_id(date(2024, 1, 15), 500.0, "Netflix")
    assert isinstance(tid, str)
    assert len(tid) == 64  # SHA256 hexdigest


def test_csv_parsing(sample_csv_content):
    transactions = parse_csv(io.BytesIO(sample_csv_content), "user-1")
    assert len(transactions) == 3
    assert transactions[0].merchant == "Swiggy"
    assert transactions[0].category == "Food"
