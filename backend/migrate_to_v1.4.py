"""Migration script: v1.4 — attachments.user_id + data isolation backfill.

为旧库补 attachments.user_id 列(若缺失),并按所属 record 的 user_id 回填,
使附件与记录遵循同一用户隔离。新库由 create_all_tables 自动建表,无需运行。

用法:
    cd backend
    python migrate_to_v1.4.py            # 默认 ./money.db
    python migrate_to_v1.4.py /path/db   # 指定库路径
"""

import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


def _db_url(argv: list[str]) -> str:
    path = argv[1] if len(argv) > 1 else "./money.db"
    return f"sqlite+aiosqlite:///{path}"


async def migrate(argv: list[str]) -> int:
    database_url = _db_url(argv)
    print(f"[v1.4 migration] target: {database_url}")
    engine = create_async_engine(database_url, echo=False)
    try:
        async with engine.begin() as conn:
            # 1. attachments 表是否存在
            exists = (
                await conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='attachments'"
                    )
                )
            ).fetchone()
            if not exists:
                print("  [SKIP] attachments 表不存在(新库将由应用自动建表)")
                return 0

            cols = [r[1] for r in (await conn.execute(text("PRAGMA table_info(attachments)"))).fetchall()]
            if "user_id" not in cols:
                await conn.execute(
                    text(
                        "ALTER TABLE attachments ADD COLUMN user_id INTEGER "
                        "REFERENCES users(id) ON DELETE CASCADE"
                    )
                )
                print("  [OK] 已为 attachments 添加 user_id 列")
            else:
                print("  [SKIP] attachments.user_id 已存在")

            # 2. 按 record 回填 user_id(仅对 user_id IS NULL 的行)
            res = await conn.execute(
                text(
                    "UPDATE attachments "
                    "SET user_id = (SELECT r.user_id FROM records r "
                    "               WHERE r.id = attachments.record_id) "
                    "WHERE attachments.user_id IS NULL "
                    "  AND attachments.record_id IS NOT NULL"
                )
            )
            print(f"  [OK] 回填 {res.rowcount} 行附件归属 user_id")

            # 3. 补索引(若缺失),加速按用户隔离查询
            idx_exists = (
                await conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='index' "
                        "AND name='ix_attachments_user_id'"
                    )
                )
            ).fetchone()
            if not idx_exists:
                await conn.execute(text("CREATE INDEX ix_attachments_user_id ON attachments(user_id)"))
                print("  [OK] 创建索引 ix_attachments_user_id")
            else:
                print("  [SKIP] 索引 ix_attachments_user_id 已存在")
    finally:
        await engine.dispose()

    print("[v1.4 migration] 完成。")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(migrate(sys.argv)))
