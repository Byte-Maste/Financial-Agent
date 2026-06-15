from services.analytics import compute_health_score


def test_health_score_perfect():
    report = compute_health_score(
        total_income=100000,
        total_expenses=30000,
        debt_payments=0,
        monthly_spending=[25000, 26000, 24000],
        current_balance=200000,
        avg_monthly_expenses=25000,
    )
    assert report.financial_health_score > 80
    assert report.savings_rate == 0.7


def test_health_score_poor():
    report = compute_health_score(
        total_income=50000,
        total_expenses=48000,
        debt_payments=10000,
        monthly_spending=[48000, 47000, 49000],
        current_balance=5000,
        avg_monthly_expenses=48000,
    )
    assert report.financial_health_score < 50
