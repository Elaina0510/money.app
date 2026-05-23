"""Database engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)


async def create_all_tables() -> None:
    """Create all tables if they don't exist (preserve existing data)."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session."""
    async with AsyncSession(engine) as session:
        yield session
