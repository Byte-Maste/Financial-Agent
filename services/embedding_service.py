import time

import voyageai

from core.config import settings
from core.logger import logger


def _voyage_configured() -> bool:
    key = settings.voyage_api_key
    return bool(key)


def get_embedding(text: str) -> list[float]:
    if not _voyage_configured():
        raise RuntimeError("Voyage AI not configured — set VOYAGE_API_KEY in .env")
    start = time.time()
    vo = voyageai.Client(api_key=settings.voyage_api_key)
    result = vo.embed([text], model=settings.embedding_model)
    elapsed = time.time() - start
    logger.info(f"Embedding | model={settings.embedding_model} | text_len={len(text)} | took={elapsed:.2f}s")
    return result.embeddings[0]
