import time

from langchain_core.messages import AIMessage
from sqlalchemy import text

from core.database import async_session_factory
from core.logger import logger
from schemas.state import AgentState
from services.category_service import categorize_transaction


async def categorization_agent(state: AgentState) -> dict:
    start = time.time()
    user_id = state["user_id"]
    async with async_session_factory() as session:
        rows = await session.execute(
            text(
                "SELECT transaction_id, merchant FROM transactions "
                "WHERE user_id = :uid AND category = 'Uncategorized' LIMIT 50"
            ),
            {"uid": user_id},
        )
        uncategorized = rows.fetchall()
    logger.info(f"Categorization | user_id={user_id} | uncategorized_found={len(uncategorized)}")

    if not uncategorized:
        elapsed = time.time() - start
        logger.info(f"Categorization done | user_id={user_id} | categorized=0 | took={elapsed:.2f}s | result=no_uncategorized_txns")
        return {
            "messages": [AIMessage(content="No uncategorized transactions found.")],
            "extracted_payload": {"categorized_count": 0},
        }

    categorized_count = 0
    async with async_session_factory() as session:
        for tid, merchant in uncategorized:
            await categorize_transaction(session, tid, merchant)
            categorized_count += 1
            logger.debug(f"Categorized | tid={tid[:12]} | merchant={merchant} | label")

    elapsed = time.time() - start
    logger.info(
        f"Categorization done | user_id={user_id} | "
        f"categorized={categorized_count}/{len(uncategorized)} | took={elapsed:.2f}s"
    )
    return {
        "messages": [AIMessage(content=f"Categorized {categorized_count} transactions.")],
        "extracted_payload": {"categorized_count": categorized_count},
    }
