from pydantic import BaseModel, Field
from typing import Literal
from datetime import date


class Transaction(BaseModel):
    transaction_id: str = Field(..., description="Unique hash from date, amount, and raw_merchant")
    user_id: str = Field(..., description="UUID of the owning user")
    transaction_date: date = Field(..., description="Calendar date the transaction was settled")
    amount: float = Field(..., gt=0, description="Absolute transaction value in local currency")
    merchant: str = Field(..., description="Cleaned merchant entity name")
    raw_merchant: str = Field(..., description="Unparsed merchant identifier from source ledger")
    category: Literal[
        "Food", "Travel", "Healthcare", "Shopping", "Bills",
        "Education", "Investments", "Subscriptions", "Uncategorized"
    ] = "Uncategorized"
    payment_mode: Literal["UPI", "Credit Card", "Debit Card", "Net Banking"] = "UPI"


class UserState(BaseModel):
    user_id: str
    current_balance: float = 0.0
    monthly_income: float = 0.0


class IngestionResult(BaseModel):
    user_id: str
    records_inserted: int = 0
    duplicates_skipped: int = 0
    errors: list[str] = []


class AnalyticsReport(BaseModel):
    user_id: str
    financial_health_score: float
    savings_rate: float
    debt_to_income_ratio: float
    spending_variance: float
    emergency_fund_months: float
    total_income: float
    total_expenses: float
    monthly_breakdown: dict[str, float]


class AnomalyReport(BaseModel):
    user_id: str
    outliers: list[dict]
    duplicates: list[dict]


class ForecastReport(BaseModel):
    user_id: str
    current_balance: float
    projected_balance_day_30: float
    daily_run_rate: float
    fixed_commitments: list[dict]
    subscriptions: list[dict]
    cash_cliff_alert: bool
    daily_balance: list[float]
