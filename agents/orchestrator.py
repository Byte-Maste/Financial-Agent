import json
import re
import time

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from core.logger import logger
from schemas.state import AgentState
from schemas.routing import OrchestratorRoutingContract
from services.llm_service import FallbackLLM
from services.notification_service import build_alerts
from agents.ingestion_agent import ingestion_agent
from agents.categorization_agent import categorization_agent
from agents.analysis_agent import analysis_agent
from agents.anomaly_agent import anomaly_agent
from agents.forecast_agent import forecast_agent
from agents.budget_agent import budget_agent
from agents.advisor_agent import advisor_agent


system_prompt = SystemMessage(
    content="You are the master selector for a financial wellness multi-agent system. "
    "Analyze the user's request and route it to the correct sub-agent:\n"
    "- 'ingest' — user wants to upload or parse financial documents (PDF, CSV, UPI text)\n"
    "- 'categorize' — user wants to categorize uncategorized transactions\n"
    "- 'analyze' — user wants spending analysis, trends, or financial health score\n"
    "- 'anomaly' — user wants fraud detection, outlier, or duplicate charge scanning\n"
    "- 'budget' — user wants budget advice or spending limits\n"
    "- 'forecast' — user wants cash flow projections or subscription insights\n"
    "- 'advise' — user wants proactive financial advice or recommendations\n"
    "- 'notify' — user wants alerts or notifications\n"
    "- 'clarify' — the request is ambiguous or needs more information\n\n"
    "Respond with the appropriate action, reasoning, and any extracted payload."
)


def _llm() -> FallbackLLM:
    return FallbackLLM()


async def master_selector(state: AgentState) -> dict:
    start = time.time()
    user_id = state.get("user_id", "unknown")
    last_message = state["messages"][-1] if state["messages"] else HumanMessage(content="")
    msg_preview = last_message.content[:80] if hasattr(last_message, "content") else "N/A"

    json_prompt = SystemMessage(
        content="You are the master selector for a financial wellness multi-agent system. "
        "Analyze the user's request and route it to the correct sub-agent.\n"
        "Respond with a JSON object with these fields:\n"
        '- "action": one of "ingest", "categorize", "analyze", "anomaly", "budget", "forecast", "advise", "notify", "clarify"\n'
        '- "reasoning": string explaining why this path was selected\n'
        '- "agent_payload": object with any extracted parameters (empty object if none)\n\n'
        "Return ONLY valid JSON, no markdown, no explanation."
    )
    llm = _llm()
    resp = await llm.ainvoke([json_prompt, last_message])
    content = resp.content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```$", "", content)
    try:
        route_data = json.loads(content)
    except json.JSONDecodeError:
        logger.error(f"Orchestrator: LLM returned non-JSON | content={content[:200]}")
        route_data = {"action": "clarify", "reasoning": "Failed to parse LLM response", "agent_payload": {}}
    route = OrchestratorRoutingContract(**route_data)

    elapsed = time.time() - start
    logger.info(
        f"Orchestrator routed | user_id={user_id} | "
        f"action={route.action} | reasoning={route.reasoning[:80]} | "
        f"msg=\"{msg_preview}\" | took={elapsed:.2f}s"
    )
    return {
        "active_route": route.action,
        "extracted_payload": {
            **route.agent_payload,
            "reasoning": route.reasoning,
        },
    }


def route_decision(state: AgentState) -> str:
    return state.get("active_route", "clarify")


async def clarify_node(state: AgentState) -> dict:
    llm = _llm()
    last_message = state["messages"][-1] if state["messages"] else HumanMessage(content="")
    logger.info(f"Clarify requested | user_id={state.get('user_id')} | msg=\"{last_message.content[:60] if hasattr(last_message, 'content') else 'N/A'}\"")
    resp = await llm.ainvoke([
        SystemMessage(content="The request is ambiguous. Ask the user to clarify what they want: "
                     "upload documents, analyze spending, forecast cash flow, or get advice."),
        last_message,
    ])
    return {"messages": [resp], "active_route": "end"}


async def notify_node(state: AgentState) -> dict:
    payload = state.get("extracted_payload", {})
    outliers = payload.get("outliers", [])
    duplicates = payload.get("duplicates", [])
    forecast = payload.get("forecast", {})
    alerts = build_alerts(forecast, outliers, duplicates)
    logger.info(f"Notifications | user_id={state.get('user_id')} | alerts={len(alerts)}")
    return {
        "messages": [AIMessage(content=str(alerts) if alerts else "No alerts.")],
        "extracted_payload": {**payload, "alerts": alerts},
    }


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("master_selector", master_selector)
    graph.add_node("clarify", clarify_node)
    graph.add_node("ingest", ingestion_agent)
    graph.add_node("categorize", categorization_agent)
    graph.add_node("analyze", analysis_agent)
    graph.add_node("anomaly", anomaly_agent)
    graph.add_node("budget", budget_agent)
    graph.add_node("forecast", forecast_agent)
    graph.add_node("advise", advisor_agent)
    graph.add_node("notify", notify_node)

    graph.set_entry_point("master_selector")

    graph.add_conditional_edges(
        "master_selector",
        route_decision,
        {
            "ingest": "ingest",
            "categorize": "categorize",
            "analyze": "analyze",
            "anomaly": "anomaly",
            "budget": "budget",
            "forecast": "forecast",
            "advise": "advise",
            "notify": "notify",
            "clarify": "clarify",
        },
    )

    for node in ["ingest", "categorize", "analyze", "anomaly", "budget", "forecast", "advise", "notify", "clarify"]:
        graph.add_edge(node, END)

    return graph


graph = build_graph()
compiled_graph = graph.compile()
