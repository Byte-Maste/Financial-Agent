import time

import pandas as pd
from langchain_core.messages import AIMessage
from sqlalchemy import text

from core.database import async_session_factory
from core.logger import logger
from schemas.state import AgentState
from services.analytics import (
    compute_health_score,
    compute_monthly_breakdown,
)
from services.anomaly_service import detect_duplicates, detect_outliers


async def analysis_agent(state: AgentState) -> dict:
    start = time.time()
    user_id = state["user_id"]

    async with async_session_factory() as session:
        user_row = await session.execute(
            text("SELECT current_balance, monthly_income FROM users WHERE user_id = :uid"),
            {"uid": user_id},
        )
        user_data = user_row.fetchone()
        current_balance = float(user_data[0]) if user_data else 0
        monthly_income = float(user_data[1]) if user_data else 0

        txn_rows = await session.execute(
            text(
                "SELECT date, amount, transaction_type, category, payment_mode "
                "FROM transactions WHERE user_id = :uid ORDER BY date ASC"
            ),
            {"uid": user_id},
        )
        data = txn_rows.fetchall()

    if not data:
        logger.info(f"Analysis done | user_id={user_id} | result=no_data | took={time.time()-start:.2f}s")
        return {
            "messages": [AIMessage(content="No transactions found for analysis.")],
            "extracted_payload": {},
        }

    df = pd.DataFrame(data, columns=["date", "amount", "transaction_type", "category", "payment_mode"])
    income_df = df[df["transaction_type"] == "credit"]
    expense_df = df[df["transaction_type"] == "debit"]

    total_income = float(income_df["amount"].sum())
    total_expenses = float(expense_df["amount"].sum())
    monthly_spending = expense_df.groupby(pd.to_datetime(expense_df["date"]).dt.month)["amount"].sum().tolist()
    avg_monthly_expenses = total_expenses / max(len(monthly_spending), 1)

    report = compute_health_score(
        total_income=max(total_income, monthly_income),
        total_expenses=total_expenses,
        debt_payments=0,
        monthly_spending=monthly_spending,
        current_balance=current_balance,
        avg_monthly_expenses=avg_monthly_expenses,
    )
    report.user_id = user_id
    report.monthly_breakdown = compute_monthly_breakdown(df)

    outliers = detect_outliers(expense_df)
    duplicates = detect_duplicates(df)

    elapsed = time.time() - start
    logger.info(
        f"Analysis done | user_id={user_id} | "
        f"fhs={report.financial_health_score} | "
        f"savings_rate={report.savings_rate:.1%} | "
        f"emergency_fund={report.emergency_fund_months:.1f}m | "
        f"income=₹{total_income:,.2f} | expenses=₹{total_expenses:,.2f} | "
        f"outliers={len(outliers)} | duplicates={len(duplicates)} | "
        f"txn_count={len(df)} | took={elapsed:.2f}s"
    )

    summary = (
        f"Financial Health Score: {report.financial_health_score}/100. "
        f"Savings rate: {report.savings_rate:.1%}. "
        f"Emergency fund: {report.emergency_fund_months:.1f} months. "
        f"Total income: ₹{total_income:,.2f}. "
        f"Total expenses: ₹{total_expenses:,.2f}. "
        f"Outliers detected: {len(outliers)}. "
        f"Duplicate charges: {len(duplicates)}."
    )
    return {
        "messages": [AIMessage(content=summary)],
        "extracted_payload": {
            "analytics": report.model_dump(),
            "outliers": outliers,
            "duplicates": duplicates,
        },
    }
