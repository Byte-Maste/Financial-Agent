import time

import pandas as pd
from langchain_core.messages import AIMessage
from sqlalchemy import text

from core.database import async_session_factory
from core.logger import logger
from schemas.state import AgentState

NEEDS_CATEGORIES = {"Bills", "Healthcare", "Education", "Food"}
WANTS_CATEGORIES = {"Shopping", "Entertainment", "Travel", "Subscriptions"}


async def budget_agent(state: AgentState) -> dict:
    start = time.time()
    user_id = state["user_id"]

    async with async_session_factory() as session:
        user_row = await session.execute(
            text("SELECT monthly_income FROM users WHERE user_id = :uid"),
            {"uid": user_id},
        )
        user_data = user_row.fetchone()
        monthly_income = float(user_data[0]) if user_data else 0

        txn_rows = await session.execute(
            text(
                "SELECT date, amount, transaction_type, category FROM transactions "
                "WHERE user_id = :uid ORDER BY date ASC"
            ),
            {"uid": user_id},
        )
        data = txn_rows.fetchall()

    if monthly_income == 0:
        logger.info(f"Budget done | user_id={user_id} | result=no_income | took={time.time()-start:.2f}s")
        return {
            "messages": [AIMessage(content="Set your monthly income in your profile to use budget planning.")],
            "extracted_payload": {},
        }

    budget_needs_target = monthly_income * 0.50
    budget_wants_target = monthly_income * 0.30
    budget_savings_target = monthly_income * 0.20

    if not data:
        budget = {
            "monthly_income": monthly_income,
            "needs_target": budget_needs_target,
            "wants_target": budget_wants_target,
            "savings_target": budget_savings_target,
            "needs_spent": 0,
            "wants_spent": 0,
            "savings_actual": budget_savings_target,
            "remaining_needs": budget_needs_target,
            "remaining_wants": budget_wants_target,
        }
        return {
            "messages": [AIMessage(content=_format_budget(budget))],
            "extracted_payload": {"budget": budget},
        }

    df = pd.DataFrame(data, columns=["date", "amount", "transaction_type", "category"])
    expense_df = df[df["transaction_type"] == "debit"]

    needs_spent = float(expense_df[expense_df["category"].isin(NEEDS_CATEGORIES)]["amount"].sum())
    wants_spent = float(expense_df[expense_df["category"].isin(WANTS_CATEGORIES)]["amount"].sum())
    savings_actual = max(0, monthly_income - needs_spent - wants_spent)

    budget = {
        "monthly_income": monthly_income,
        "needs_target": budget_needs_target,
        "wants_target": budget_wants_target,
        "savings_target": budget_savings_target,
        "needs_spent": round(needs_spent, 2),
        "wants_spent": round(wants_spent, 2),
        "savings_actual": round(savings_actual, 2),
        "remaining_needs": round(max(0, budget_needs_target - needs_spent), 2),
        "remaining_wants": round(max(0, budget_wants_target - wants_spent), 2),
    }

    elapsed = time.time() - start
    logger.info(
        f"Budget done | user_id={user_id} | "
        f"income=₹{monthly_income:,.2f} | "
        f"needs=₹{needs_spent:,.2f}/{budget_needs_target:,.2f} | "
        f"wants=₹{wants_spent:,.2f}/{budget_wants_target:,.2f} | "
        f"took={elapsed:.2f}s"
    )

    return {
        "messages": [AIMessage(content=_format_budget(budget))],
        "extracted_payload": {"budget": budget},
    }


def _format_budget(b: dict) -> str:
    lines = [
        f"Monthly Income: ₹{b['monthly_income']:,.2f}",
        "",
        "50/30/20 Budget Breakdown:",
        f"  Needs (50%): ₹{b['needs_spent']:,.2f} spent of ₹{b['needs_target']:,.2f} target (₹{b['remaining_needs']:,.2f} remaining)",
        f"  Wants (30%): ₹{b['wants_spent']:,.2f} spent of ₹{b['wants_target']:,.2f} target (₹{b['remaining_wants']:,.2f} remaining)",
        f"  Savings (20%): ₹{b['savings_actual']:,.2f} actual of ₹{b['savings_target']:,.2f} target",
    ]

    if b["needs_spent"] > b["needs_target"]:
        lines.append(f"\n⚠ Overspent on Needs by ₹{b['needs_spent'] - b['needs_target']:,.2f}")
    if b["wants_spent"] > b["wants_target"]:
        lines.append(f"⚠ Overspent on Wants by ₹{b['wants_spent'] - b['wants_target']:,.2f}")
    if b["savings_actual"] < b["savings_target"]:
        lines.append(f"⚠ Savings shortfall of ₹{b['savings_target'] - b['savings_actual']:,.2f}")

    return "\n".join(lines)
