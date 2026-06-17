import time

from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage, SystemMessage

from core.logger import logger
from schemas.state import AgentState
from services.llm_service import FallbackLLM


async def investment_readiness_agent(state: AgentState) -> dict:
    start = time.time()
    payload = state.get("extracted_payload", {})
    analytics = payload.get("analytics", {})
    forecast = payload.get("forecast", {})

    emergency_fund_months = analytics.get("emergency_fund_months", 0)
    cash_cliff = forecast.get("cash_cliff_alert", True) if forecast else True
    savings_rate = analytics.get("savings_rate", 0)

    checks = []
    if emergency_fund_months >= 6:
        checks.append("✅ Emergency fund: adequate (>= 6 months)")
    else:
        checks.append(f"❌ Emergency fund: {emergency_fund_months:.1f} months — needs 6+ months")

    if not cash_cliff:
        checks.append("✅ No cash cliff detected")
    else:
        checks.append("❌ Cash cliff detected — address before investing")

    if savings_rate >= 0.20:
        checks.append(f"✅ Savings rate: {savings_rate:.0%} (meets 20% target)")
    else:
        checks.append(f"⚠ Savings rate: {savings_rate:.0%} — below 20% target")

    ready = emergency_fund_months >= 6 and not cash_cliff and savings_rate >= 0.20
    verdict = "Ready to invest 🚀" if ready else "Not ready — complete prerequisites first"

    context = "\n".join(checks)

    llm = FallbackLLM()
    resp = await llm.ainvoke([
        SystemMessage(content="You are an investment readiness advisor. Give concise, actionable advice "
                     "based on the readiness check results provided."),
        HumanMessage(content=f"Readiness check:\n{context}\n\nVerdict: {verdict}\n\nProvide advice."),
    ])

    elapsed = time.time() - start
    logger.info(
        f"Investment readiness done | ready={ready} | "
        f"ef={emergency_fund_months:.1f}m | cliff={cash_cliff} | "
        f"savings={savings_rate:.0%} | took={elapsed:.2f}s"
    )

    return {
        "messages": [AIMessage(content=resp.content)],
        "extracted_payload": {
            "investment_readiness": {
                "ready": ready,
                "checks": checks,
                "verdict": verdict,
            }
        },
    }
