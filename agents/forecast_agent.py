import time

import pandas as pd
from langchain_core.messages import AIMessage
from sqlalchemy import text

from core.database import async_session_factory
from core.logger import logger
from schemas.state import AgentState
from services.forecaster import forecast_cash_flow
from services.subscription_service import detect_recurring_charges, flag_inactive_subscriptions


async def forecast_agent(state: AgentState) -> dict:
    start = time.time()
    user_id = state["user_id"]

    async with async_session_factory() as session:
        user_row = await session.execute(
            text("SELECT current_balance FROM users WHERE user_id = :uid"),
            {"uid": user_id},
        )
        user_data = user_row.fetchone()
        current_balance = float(user_data[0]) if user_data else 0

        txn_rows = await session.execute(
            text(
                "SELECT date, amount, merchant, category FROM transactions "
                "WHERE user_id = :uid ORDER BY date ASC"
            ),
            {"uid": user_id},
        )
        data = txn_rows.fetchall()

    if not data:
        logger.info(f"Forecast done | user_id={user_id} | result=no_data | took={time.time()-start:.2f}s")
        return {
            "messages": [AIMessage(content="No data available for forecasting.")],
            "extracted_payload": {},
        }

    df = pd.DataFrame(data, columns=["date", "amount", "merchant", "category"])
    subs = detect_recurring_charges(df)
    inactive = flag_inactive_subscriptions(subs, df)
    forecast = forecast_cash_flow(current_balance, df)

    elapsed = time.time() - start
    logger.info(
        f"Forecast done | user_id={user_id} | "
        f"balance=₹{current_balance:,.2f} | "
        f"projected_30d=₹{forecast['projected_balance_day_30']:,.2f} | "
        f"run_rate=₹{forecast['daily_run_rate']:,.2f}/day | "
        f"subscriptions={len(subs)} | inactive={len(inactive)} | "
        f"cliff_alert={forecast['cash_cliff_alert']} | "
        f"txn_count={len(df)} | took={elapsed:.2f}s"
    )

    summary_parts = [
        f"Projected balance in 30 days: ₹{forecast['projected_balance_day_30']:,.2f}",
        f"Daily run rate: ₹{forecast['daily_run_rate']:,.2f}",
    ]
    if forecast["cash_cliff_alert"]:
        summary_parts.append("⚠ Cash cliff alert: projected balance may run low!")
    if inactive:
        summary_parts.append(f"Unused subscriptions: {len(inactive)} — consider canceling.")
    summary = ". ".join(summary_parts)

    return {
        "messages": [AIMessage(content=summary)],
        "extracted_payload": {
            "forecast": forecast,
            "subscriptions": subs,
            "inactive_subscriptions": inactive,
        },
    }
