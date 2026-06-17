from agents.analysis_agent import analysis_agent
from agents.anomaly_agent import anomaly_agent
from agents.forecast_agent import forecast_agent
from agents.budget_agent import budget_agent
from schemas.state import AgentState
from services.notification_service import build_alerts, get_unread_alerts, persist_alerts
from core.database import async_session_factory


def _make_state(user_id: str) -> AgentState:
    return AgentState(
        messages=[],
        user_id=user_id,
        active_route="",
        extracted_payload={},
    )


async def run_full_pipeline(user_id: str) -> dict:
    state = _make_state(user_id)
    payload: dict = {}

    ana = await analysis_agent(state)
    payload.update(ana.get("extracted_payload", {}))
    state["extracted_payload"] = payload

    ano = await anomaly_agent(state)
    payload.update(ano.get("extracted_payload", {}))
    state["extracted_payload"] = payload

    fct = await forecast_agent(state)
    payload.update(fct.get("extracted_payload", {}))
    state["extracted_payload"] = payload

    budget = await budget_agent(state)
    payload.update(budget.get("extracted_payload", {}))
    state["extracted_payload"] = payload

    alerts = build_alerts(
        forecast=payload.get("forecast"),
        outliers=payload.get("outliers", []),
        duplicates=payload.get("duplicates", []),
        budget=payload.get("budget"),
        analytics=payload.get("analytics"),
        inactive_subscriptions=payload.get("inactive_subscriptions", []),
    )
    payload["alerts"] = alerts

    async with async_session_factory() as session:
        await persist_alerts(session, user_id, alerts)
        unread = await get_unread_alerts(session, user_id)
    payload["active_alerts"] = unread

    return payload
