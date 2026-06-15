from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage

from agents.orchestrator import compiled_graph
from core.logger import logger

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.websocket("/ws")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket client connected")
    try:
        while True:
            data = await websocket.receive_json()
            user_id = data.get("user_id", "")
            message = data.get("message", "")
            logger.info(f"WS message | user_id={user_id} | msg_preview={message[:60]}")
            result = await compiled_graph.ainvoke({
                "messages": [HumanMessage(content=message)],
                "user_id": user_id,
                "active_route": "",
                "extracted_payload": {},
            })
            response_text = result["messages"][-1].content if result.get("messages") else ""
            logger.info(f"WS response | user_id={user_id} | route={result.get('active_route')} | response_len={len(response_text)}")
            await websocket.send_json({
                "route": result.get("active_route"),
                "response": response_text,
            })
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
