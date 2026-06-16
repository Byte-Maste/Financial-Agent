import numpy as np
import pandas as pd

from schemas.models import AnalyticsReport

W1 = 30
W2 = 20
W3 = 20
W4 = 30


def compute_health_score(
    total_income: float,
    total_expenses: float,
    debt_payments: float,
    monthly_spending: list[float],
    current_balance: float,
    avg_monthly_expenses: float,
) -> AnalyticsReport:
    savings_rate = (total_income - total_expenses) / total_income if total_income > 0 else 0
    debt_to_income = debt_payments / total_income if total_income > 0 else 0
    spending_array = np.array([float(x) for x in monthly_spending]) if monthly_spending else np.array([0.0])
    spending_variance = 1 - (float(np.std(spending_array)) / float(np.mean(spending_array) + 1e-8))
    emergency_fund_months = current_balance / avg_monthly_expenses if avg_monthly_expenses > 0 else 0
    emergency_score = min(1, emergency_fund_months / 6)

    fhs = (
        W1 * savings_rate
        + W2 * (1 - debt_to_income)
        + W3 * spending_variance
        + W4 * emergency_score
    )
    fhs = max(0, min(100, fhs))

    return AnalyticsReport(
        user_id="",
        financial_health_score=round(fhs, 1),
        savings_rate=round(savings_rate, 4),
        debt_to_income_ratio=round(debt_to_income, 4),
        spending_variance=round(spending_variance, 4),
        emergency_fund_months=round(emergency_fund_months, 2),
        total_income=round(total_income, 2),
        total_expenses=round(total_expenses, 2),
        monthly_breakdown={},
    )


def compute_monthly_breakdown(
    df: pd.DataFrame,
) -> dict[str, float]:
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
    return df.groupby("month")["amount"].sum().to_dict()


def compute_category_breakdown(df: pd.DataFrame) -> dict[str, float]:
    return df.groupby("category")["amount"].sum().to_dict()
