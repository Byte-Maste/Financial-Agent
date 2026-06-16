import json

import numpy as np
from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import logger
from services.embedding_service import get_embedding
from services.llm_service import FallbackLLM

CATEGORIES = [
    "Food", "Travel", "Healthcare", "Shopping", "Bills",
    "Education", "Investments", "Subscriptions", "Uncategorized",
]

SIMILARITY_THRESHOLD = 0.75

zero_shot_prompt = SystemMessage(
    content=f"Classify the given merchant name into exactly one category: {', '.join(CATEGORIES)}. "
    "Respond with ONLY the category name, nothing else."
)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    a_arr = np.array(a, dtype=np.float32)
    b_arr = np.array(b, dtype=np.float32)
    return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr) + 1e-10))


async def _find_similar_merchant(
    session: AsyncSession, embedding: list[float]
) -> str | None:
    rows = await session.execute(
        text("SELECT merchant_name, category, embedding FROM merchant_embeddings")
    )
    best_score = 0.0
    best_category = None
    for row in rows.fetchall():
        stored_embedding = row.embedding
        score = _cosine_similarity(embedding, stored_embedding)
        if score > best_score:
            best_score = score
            best_category = row.category
    if best_score >= SIMILARITY_THRESHOLD and best_category:
        return best_category
    return None


async def _upsert_merchant_embedding(
    session: AsyncSession, merchant_name: str, category: str, embedding: list[float]
) -> None:
    await session.execute(
        text(
            "INSERT INTO merchant_embeddings (merchant_name, category, embedding) "
            "VALUES (:name, :cat, :emb) "
            "ON CONFLICT (merchant_name) DO UPDATE SET category = :cat2, embedding = :emb2"
        ),
        {
            "name": merchant_name,
            "cat": category,
            "emb": json.dumps(embedding),
            "cat2": category,
            "emb2": json.dumps(embedding),
        },
    )
    await session.commit()


async def classify_with_llm(merchant_name: str) -> str:
    llm = FallbackLLM()
    resp = await llm.ainvoke([zero_shot_prompt, HumanMessage(content=merchant_name)])
    category = resp.content.strip()
    if category in CATEGORIES:
        logger.debug(f"LLM classified | merchant={merchant_name} | category={category}")
        return category
    logger.warning(f"LLM returned invalid category | merchant={merchant_name} | response={category} | fallback=Uncategorized")
    return "Uncategorized"


async def categorize_transaction(
    session: AsyncSession, transaction_id: str, merchant_name: str,
    embedding: list[float] | None = None,
) -> str:
    if embedding is None:
        try:
            embedding = get_embedding(merchant_name)
        except RuntimeError:
            embedding = None

    if embedding:
        similar = await _find_similar_merchant(session, embedding)
        if similar:
            logger.debug(f"Embedding match | merchant={merchant_name} | category={similar}")
            await session.execute(
                text("UPDATE transactions SET category = :cat WHERE transaction_id = :tid"),
                {"cat": similar, "tid": transaction_id},
            )
            await session.commit()
            return similar

    category = await classify_with_llm(merchant_name)

    if embedding:
        await _upsert_merchant_embedding(session, merchant_name, category, embedding)

    await session.execute(
        text("UPDATE transactions SET category = :cat WHERE transaction_id = :tid"),
        {"cat": category, "tid": transaction_id},
    )
    await session.commit()
    logger.debug(f"Categorized | tid={transaction_id[:12]} | merchant={merchant_name} | label={category}")
    return category
