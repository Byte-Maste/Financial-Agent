import pandas as pd
from services.anomaly_service import detect_duplicates, detect_outliers


def test_detect_duplicates():
    df = pd.DataFrame({
        "date": ["2024-01-15 10:00:00", "2024-01-15 10:00:30"],
        "amount": [500.0, 500.0],
        "merchant": ["Netflix", "Netflix"],
        "category": ["Subscriptions", "Subscriptions"],
        "transaction_id": ["t1", "t2"],
    })
    dups = detect_duplicates(df)
    assert len(dups) == 1
    assert dups[0]["merchant"] == "Netflix"


def test_no_duplicates_for_different_merchants():
    df = pd.DataFrame({
        "date": ["2024-01-15", "2024-01-15"],
        "amount": [500.0, 500.0],
        "merchant": ["Netflix", "Spotify"],
        "category": ["Subscriptions", "Subscriptions"],
        "transaction_id": ["t1", "t2"],
    })
    dups = detect_duplicates(df)
    assert len(dups) == 0
