import time

import pandas as pd
from langchain_core.messages import AIMessage
from sqlalchemy import text

from core.database import async_session_factory
from core.logger import logger
from schemas.state import AgentState
from services.anomaly_service import detect_duplicates, detect_outliers


async def anomaly_agent(state: AgentState) -> dict:
    start = time.time()
    user_id = state["user_id"]

    async with async_session_factory() as session:
        rows = await session.execute(
            text(
                "SELECT date, amount, merchant, category, payment_mode "
                "FROM transactions WHERE user_id = :uid ORDER BY date ASC"
            ),
            {"uid": user_id},
        )
        data = rows.fetchall()

    if not data:
        logger.info(f"Anomaly scan done | user_id={user_id} | result=no_data | took={time.time()-start:.2f}s")
        return {
            "messages": [AIMessage(content="No transactions to scan for anomalies.")],
            "extracted_payload": {},
        }

    df = pd.DataFrame(data, columns=["date", "amount", "merchant", "category", "payment_mode"])
    outliers = detect_outliers(df)
    duplicates = detect_duplicates(df)

    elapsed = time.time() - start
    logger.info(
        f"Anomaly scan done | user_id={user_id} | "
        f"outliers={len(outliers)} | duplicates={len(duplicates)} | "
        f"txn_scanned={len(df)} | took={elapsed:.2f}s"
    )

    summary = f"Found {len(outliers)} outlier(s) and {len(duplicates)} duplicate charge(s)."
    return {
        "messages": [AIMessage(content=summary)],
        "extracted_payload": {"outliers": outliers, "duplicates": duplicates},
    }
