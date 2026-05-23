"""Migration script: add user_id columns for v1.2 data isolation."""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = "sqlite+aiosqlite:///./money.db"

TABLES = ["records", "budgets", "categories", "tags"]


async def migrate():
    """Add user_id columns to tables if they don't exist."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        for table in TABLES:
            result = await conn.execute(text(f"PRAGMA table_info({table})"))
            rows = result.fetchall()
            columns = [row[1] for row in rows]
            if "user_id" not in columns:
                await conn.execute(
                    text(
                        f"ALTER TABLE {table} ADD COLUMN user_id INTEGER "
                        f"REFERENCES users(id) ON DELETE CASCADE"
                    )
                )
                await conn.commit()
                print(f"  [OK] Added user_id to {table}")
            else:
                print(f"  [SKIP] user_id already exists in {table}")
    await engine.dispose()
    print("Migration completed.")


if __name__ == "__main__":
    asyncio.run(migrate())
