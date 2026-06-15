import time
from typing import Any

from pgvector.asyncpg import register_vector
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from core.config import settings
from core.logger import logger

_sanitized_url = (
    f"{settings.database_url.split('@')[0].split('://')[0]}://***@"
    f"{settings.database_url.split('@')[1] if '@' in settings.database_url else 'localhost'}"
)

engine = create_async_engine(settings.database_url, echo=False, pool_size=5, max_overflow=10)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _register_pgvector(dbapi_connection: Any, connection_record: Any) -> None:
    """Register the pgvector type codec so VECTOR columns return Python lists."""
    register_vector(dbapi_connection)


async def verify_db_connection() -> bool:
    try:
        start = time.time()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        elapsed = time.time() - start
        logger.info(f"Database connected | url={_sanitized_url} | took={elapsed:.2f}s | status=OK")
        return True
    except Exception as e:
        logger.error(f"Database connection FAILED | url={_sanitized_url} | error={e}")
        return False


async def get_session():
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Session error: {e}")
            raise
