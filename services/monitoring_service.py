import time

from sqlalchemy import text

from agents.anomaly_agent import anomaly_agent
from agents.forecast_agent import forecast_agent
from core.database import async_session_factory
from core.logger import logger
from schemas.state import AgentState
from services.analytics import detect_category_trends
from services.notification_service import build_alerts, persist_alerts


def _make_state(user_id: str) -> AgentState:
    return AgentState(
        messages=[],
        user_id=user_id,
        active_route="",
        extracted_payload={},
    )


async def run_monitoring_sweep() -> None:
    start = time.time()
    logger.info("Monitoring sweep started")
    async with async_session_factory() as session:
        rows = await session.execute(text("SELECT user_id FROM users"))
        user_ids = [r[0] for r in rows.fetchall()]
    total_alerts = 0
    for uid in user_ids:
        try:
            user_start = time.time()
            state = _make_state(uid)
            ano = await anomaly_agent(state)
            state["extracted_payload"].update(ano.get("extracted_payload", {}))
            fct = await forecast_agent(state)
            state["extracted_payload"].update(fct.get("extracted_payload", {}))
            payload = state.get("extracted_payload", {})
            category_trends = detect_category_trends(
                __df_from_payload(payload, uid)
            )
            if category_trends:
                payload["category_trends"] = category_trends
            alerts = build_alerts(
                forecast=payload.get("forecast"),
                outliers=payload.get("outliers", []),
                duplicates=payload.get("duplicates", []),
                inactive_subscriptions=payload.get("inactive_subscriptions", []),
            )
            if alerts:
                async with async_session_factory() as db_session:
                    await persist_alerts(db_session, uid, alerts)
                total_alerts += len(alerts)
            elapsed = time.time() - user_start
            logger.info(
                f"Monitoring sweep | user_id={uid} | "
                f"alerts_generated={len(alerts)} | took={elapsed:.2f}s"
            )
        except Exception as e:
            logger.error(f"Monitoring sweep failed for user {uid}: {e}")
    total_elapsed = time.time() - start
    logger.info(
        f"Monitoring sweep complete | "
        f"users={len(user_ids)} | total_alerts={total_alerts} | "
        f"took={total_elapsed:.2f}s"
    )


def __df_from_payload(payload: dict, user_id: str):
    import pandas as pd
    expenses = []
    for key in ("outliers",):
        items = payload.get(key, [])
        for item in items:
            if "amount" in item and "date" in item:
                expenses.append({"date": item["date"], "amount": item["amount"], "category": item.get("category", "Uncategorized")})
    if not expenses:
        return pd.DataFrame(columns=["date", "amount", "category"])
    return pd.DataFrame(expenses)
