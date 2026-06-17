from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

from core.database import async_session_factory
from core.logger import logger
from services.forecaster import forecast_cash_flow
from sqlalchemy import text
import pandas as pd

router = APIRouter(prefix="/api/v1", tags=["simulation"])


class SimulationRequest(BaseModel):
    user_id: str
    event_type: Literal["new_loan", "new_expense"]
    amount: float
    tenure_months: int | None = None
    interest_rate: float | None = None


@router.post("/simulate")
async def simulate(body: SimulationRequest):
    async with async_session_factory() as session:
        user_row = await session.execute(
            text("SELECT current_balance FROM users WHERE user_id = :uid"),
            {"uid": body.user_id},
        )
        current_balance = float(user_row.fetchone()[0]) if user_row.fetchone() else 0

        txn_rows = await session.execute(
            text("SELECT date, amount, transaction_type FROM transactions "
                 "WHERE user_id = :uid ORDER BY date ASC"),
            {"uid": body.user_id},
        )
        data = txn_rows.fetchall()

    df = pd.DataFrame(data, columns=["date", "amount", "transaction_type"])
    expense_df = df[df["transaction_type"] == "debit"] if not df.empty else df

    # Baseline forecast (before event)
    before = forecast_cash_flow(current_balance, expense_df)

    # Apply event
    monthly_impact = 0.0
    if body.event_type == "new_loan" and body.tenure_months and body.interest_rate:
        monthly_rate = body.interest_rate / 12 / 100
        emi = body.amount * monthly_rate * (1 + monthly_rate) ** body.tenure_months / \
              ((1 + monthly_rate) ** body.tenure_months - 1)
        monthly_impact = round(emi, 2)
        impact_desc = f"New loan EMI: ₹{monthly_impact:,.2f}/month for {body.tenure_months} months"
    elif body.event_type == "new_expense":
        monthly_impact = body.amount
        impact_desc = f"New recurring expense: ₹{monthly_impact:,.2f}/month"
    else:
        impact_desc = "No financial impact computed"

    # Forecast after event
    new_fixed = [monthly_impact]
    after = forecast_cash_flow(current_balance, expense_df, fixed_commitments=new_fixed)

    logger.info(
        f"Simulation | user_id={body.user_id} | event={body.event_type} | "
        f"amount={body.amount} | before_30d={before['projected_balance_day_30']} | "
        f"after_30d={after['projected_balance_day_30']}"
    )

    return {
        "event": impact_desc,
        "before": before,
        "after": after,
        "delta_30d": round(after["projected_balance_day_30"] - before["projected_balance_day_30"], 2),
    }
