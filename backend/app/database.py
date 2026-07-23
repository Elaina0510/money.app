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
    """Provide an async database session.

    expire_on_commit=False:async SQLAlchemy 推荐设置,避免 commit 后访问
    ORM 对象属性时触发隐式 lazy-refresh(会抛 MissingGreenlet)。
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
