import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage

from api.v1 import ingestion, chat, advisor
from agents.orchestrator import compiled_graph
from core.config import settings
from core.database import register_pgvector_codec, verify_db_connection
from core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Financial Wellness Agent server")
    db_ok = await verify_db_connection()
    if not db_ok:
        logger.warning("Server started without database — most endpoints will fail")
    else:
        await register_pgvector_codec()
        logger.info("pgvector codec registered for VECTOR column support")
    yield
    logger.info("Shutting down Financial Wellness Agent server")


app = FastAPI(
    title="Autonomous Financial Wellness Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingestion.router)
app.include_router(chat.router)
app.include_router(advisor.router)


@app.get("/health")
async def health():
    return {"status": "healthy", "llm_model": settings.llm_model, "llm_key_set": bool(settings.groq_api_key)}


@app.post("/chat")
async def chat_sync(user_id: str, message: str):
    start = time.time()
    logger.info(f"Chat request | user_id={user_id} | message_len={len(message)}")
    result = await compiled_graph.ainvoke({
        "messages": [HumanMessage(content=message)],
        "user_id": user_id,
        "active_route": "",
        "extracted_payload": {},
    })
    route = result.get("active_route", "unknown")
    elapsed = time.time() - start
    logger.info(f"Chat response | user_id={user_id} | route={route} | took={elapsed:.2f}s")
    return result
