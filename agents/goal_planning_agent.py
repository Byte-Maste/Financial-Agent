import time
from datetime import date

from langchain_core.messages import AIMessage
from sqlalchemy import text

from core.database import async_session_factory
from core.logger import logger
from schemas.state import AgentState


async def goal_planning_agent(state: AgentState) -> dict:
    start = time.time()
    user_id = state["user_id"]
    async with async_session_factory() as session:
        user_row = await session.execute(
            text("SELECT monthly_income FROM users WHERE user_id = :uid"),
            {"uid": user_id},
        )
        monthly_income = float(user_row.fetchone()[0]) if user_row.fetchone() else 0

        goal_rows = await session.execute(
            text("SELECT name, target_amount, target_date, current_progress "
                 "FROM goals WHERE user_id = :uid ORDER BY target_date ASC"),
            {"uid": user_id},
        )
        goals = goal_rows.fetchall()

    if not goals:
        return {
            "messages": [AIMessage(content="No financial goals found. Create one to start tracking!")],
            "extracted_payload": {"goal_status": []},
        }

    goal_statuses = []
    for g in goals:
        name, target_amount, target_date, current_progress = g
        target_amount = float(target_amount)
        current_progress = float(current_progress)
        remaining = target_amount - current_progress
        months_left = max((target_date - date.today()).days / 30, 1)
        required_monthly = remaining / months_left
        goal_statuses.append({
            "name": name,
            "target_amount": target_amount,
            "target_date": str(target_date),
            "current_progress": current_progress,
            "remaining": round(remaining, 2),
            "months_left": round(months_left, 1),
            "required_monthly_savings": round(required_monthly, 2),
            "on_track": required_monthly <= (monthly_income * 0.2),
        })

    elapsed = time.time() - start
    logger.info(f"Goal planning done | user_id={user_id} | goals={len(goals)} | took={elapsed:.2f}s")

    summary_parts = []
    for gs in goal_statuses:
        status = "on track" if gs["on_track"] else "needs attention"
        summary_parts.append(
            f"{gs['name']}: ₹{gs['remaining']:,.2f} remaining, "
            f"need ₹{gs['required_monthly_savings']:,.2f}/month ({status})"
        )
    summary = "\n".join(summary_parts)

    return {
        "messages": [AIMessage(content=summary or "No goals to track.")],
        "extracted_payload": {"goal_status": goal_statuses},
    }
