import time

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

from core.logger import logger
from schemas.state import AgentState
from schemas.routing import OrchestratorRoutingContract
from services.llm_service import FallbackLLM
from agents.ingestion_agent import ingestion_agent
from agents.categorization_agent import categorization_agent
from agents.analysis_agent import analysis_agent
from agents.anomaly_agent import anomaly_agent
from agents.forecast_agent import forecast_agent
from agents.advisor_agent import advisor_agent


system_prompt = SystemMessage(
    content="You are the master selector for a financial wellness multi-agent system. "
    "Analyze the user's request and route it to the correct sub-agent:\n"
    "- 'ingest' — user wants to upload or parse financial documents (PDF, CSV, UPI text)\n"
    "- 'categorize' — user wants to categorize uncategorized transactions\n"
    "- 'analyze' — user wants spending analysis, trends, or financial health score\n"
    "- 'budget' — user wants budget advice or spending limits\n"
    "- 'forecast' — user wants cash flow projections or subscription insights\n"
    "- 'advise' — user wants proactive financial advice or recommendations\n"
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

    llm = _llm().with_structured_output(OrchestratorRoutingContract)
    route = await llm.ainvoke([system_prompt, last_message])

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


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("master_selector", master_selector)
    graph.add_node("clarify", clarify_node)
    graph.add_node("ingest", ingestion_agent)
    graph.add_node("categorize", categorization_agent)
    graph.add_node("analyze", analysis_agent)
    graph.add_node("budget", analysis_agent)
    graph.add_node("forecast", forecast_agent)
    graph.add_node("advise", advisor_agent)

    graph.set_entry_point("master_selector")

    graph.add_conditional_edges(
        "master_selector",
        route_decision,
        {
            "ingest": "ingest",
            "categorize": "categorize",
            "analyze": "analyze",
            "budget": "budget",
            "forecast": "forecast",
            "advise": "advise",
            "clarify": "clarify",
        },
    )

    for node in ["ingest", "categorize", "analyze", "budget", "forecast", "advise", "clarify"]:
        graph.add_edge(node, END)

    return graph


graph = build_graph()
compiled_graph = graph.compile()
