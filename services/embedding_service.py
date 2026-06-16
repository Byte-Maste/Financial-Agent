import time

import voyageai

from core.config import settings
from core.logger import logger


def _voyage_configured() -> bool:
    key = settings.voyage_api_key
    return bool(key)


_vo_client: voyageai.Client | None = None


def _get_client() -> voyageai.Client:
    global _vo_client
    if _vo_client is None:
        if not _voyage_configured():
            raise RuntimeError("Voyage AI not configured — set VOYAGE_API_KEY in .env")
        _vo_client = voyageai.Client(api_key=settings.voyage_api_key)
    return _vo_client


def get_embedding(text: str) -> list[float]:
    return get_embeddings([text])[0]


def get_embeddings(texts: list[str]) -> list[list[float]]:
    client = _get_client()
    start = time.time()
    result = client.embed(texts, model=settings.embedding_model)
    elapsed = time.time() - start
    logger.info(f"Embeddings | model={settings.embedding_model} | count={len(texts)} | took={elapsed:.2f}s")
    return result.embeddings
