import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from core.logger import logger
from schemas.state import AgentState
from services.llm_service import FallbackLLM

SYSTEM_PROMPT = SystemMessage(
    content="You are a proactive financial advisor. You must NOT produce passive retrospective summaries "
    "(e.g., 'You spent ₹10,000 on food delivery last month'). "
    "Instead, produce forward-looking, actionable insights that quantify potential savings or impacts. "
    "Example: 'Reducing food delivery orders by two per week will recover approximately ₹18,000 annually, "
    "securing your incomplete emergency fund baseline.'\n\n"
    "Base your advice on the metrics provided below. Be specific with numbers."
)


async def advisor_agent(state: AgentState) -> dict:
    start = time.time()
    payload = state.get("extracted_payload", {})
    analytics = payload.get("analytics", {})
    forecast = payload.get("forecast", {})
    outliers = payload.get("outliers", [])
    duplicates = payload.get("duplicates", [])
    subscriptions = payload.get("subscriptions", [])
    inactive_subs = payload.get("inactive_subscriptions", [])
    category_trends = payload.get("category_trends", [])

    context_parts = []

    if analytics:
        context_parts.append(
            f"Financial Health Score: {analytics.get('financial_health_score')}/100. "
            f"Savings rate: {analytics.get('savings_rate')}. "
            f"Emergency fund: {analytics.get('emergency_fund_months')} months."
        )

    if forecast:
        context_parts.append(
            f"Current balance: {forecast.get('current_balance')}. "
            f"Projected balance in 30 days: {forecast.get('projected_balance_day_30')}. "
            f"Daily run rate: {forecast.get('daily_run_rate')}."
        )
        if forecast.get("cash_cliff_alert"):
            context_parts.append("Low balance alert: cash cliff detected.")

    if outliers:
        context_parts.append(f"{len(outliers)} unusual spending outliers detected.")

    if duplicates:
        context_parts.append(f"{len(duplicates)} possible duplicate charges found.")

    if inactive_subs:
        names = [s.get("merchant") for s in inactive_subs]
        context_parts.append(f"Inactive subscriptions: {', '.join(names)}.")
    elif subscriptions:
        context_parts.append(f"{len(subscriptions)} recurring subscriptions identified.")

    if category_trends:
        rising = [t for t in category_trends if t["trend"] == "increasing"]
        if rising:
            names = [f"{t['category']} (+{t['pct_change']:.0f}%)" for t in rising]
            context_parts.append(f"Rising spending categories: {', '.join(names)}.")

    context = "\n".join(context_parts) if context_parts else "No financial data available yet."
    logger.info(f"Advisor generating | user_id={state.get('user_id')} | context_metrics={len(context_parts)}")

    llm = FallbackLLM()
    resp = await llm.ainvoke([
        SYSTEM_PROMPT,
        HumanMessage(content=f"Here is the user's financial data:\n{context}\n\nProvide actionable advice."),
    ])

    elapsed = time.time() - start
    logger.info(f"Advisor done | user_id={state.get('user_id')} | response_len={len(resp.content)} | took={elapsed:.2f}s")

    return {
        "messages": [AIMessage(content=resp.content)],
    }
