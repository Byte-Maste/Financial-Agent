from core.database import get_session


async def get_db():
    async for session in get_session():
        yield session
