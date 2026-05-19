"""Test configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import app
from app.database import get_session
from app.models.category import Category

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

# Set default asyncio mode for all test functions
pytestmark = pytest.mark.asyncio


async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    """Override the database session dependency for tests."""
    async with AsyncSession(test_engine) as session:
        yield session


PRESET_CATEGORIES = [
    {"name": "餐饮", "type": "expense", "icon": "mdi-food", "sort_order": 1},
    {"name": "交通", "type": "expense", "icon": "mdi-bus", "sort_order": 2},
    {"name": "购物", "type": "expense", "icon": "mdi-cart", "sort_order": 3},
    {"name": "工资", "type": "income", "icon": "mdi-cash", "sort_order": 1},
    {"name": "其他收入", "type": "income", "icon": "mdi-cash-plus", "sort_order": 2},
]


async def seed_categories(db: AsyncSession):
    """Insert preset categories into the database."""
    for cat_data in PRESET_CATEGORIES:
        category = Category(
            name=cat_data["name"],
            type=cat_data["type"],
            icon=cat_data["icon"],
            sort_order=cat_data["sort_order"],
            is_preset=1,
        )
        db.add(category)
    await db.commit()


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create all tables before each test and seed preset data."""
    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Seed preset categories
    async with AsyncSession(test_engine) as session:
        await seed_categories(session)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with AsyncSession(test_engine) as session:
        yield session

