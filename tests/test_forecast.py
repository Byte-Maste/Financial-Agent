import pandas as pd
from services.forecaster import forecast_cash_flow
from services.subscription_service import detect_recurring_charges


def test_forecast_projection():
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=30, freq="D"),
        "amount": [500.0] * 30,
        "merchant": ["Test"] * 30,
        "category": ["Food"] * 30,
    })
    result = forecast_cash_flow(current_balance=50000, df=df)
    assert result["current_balance"] == 50000
    assert result["projected_balance_day_30"] < 50000
    assert "daily_balance" in result


def test_recurring_detection():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "amount": [999.0, 999.0, 999.0],
        "merchant": ["Netflix", "Netflix", "Netflix"],
        "category": ["Subscriptions", "Subscriptions", "Subscriptions"],
    })
    subs = detect_recurring_charges(df)
    assert len(subs) == 1
    assert subs[0]["frequency"] == "monthly"
