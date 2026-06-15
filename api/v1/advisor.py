from fastapi import APIRouter
from langchain_core.messages import HumanMessage

from agents.orchestrator import compiled_graph

router = APIRouter(prefix="/api/v1", tags=["advisor"])


@router.get("/advice/{user_id}")
async def get_advice(user_id: str):
    result = await compiled_graph.ainvoke({
        "messages": [HumanMessage(content="Analyze my finances and give me advice.")],
        "user_id": user_id,
        "active_route": "",
        "extracted_payload": {},
    })
    return result
