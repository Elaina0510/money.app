"""Migration script: v1.4.2 — quick_templates.kind column (M6 自动模板按签名忽略).

为旧库补 quick_templates.kind 列(若缺失),默认值 'manual' 使既有手动模板语义不变;
新库由 create_all_tables 自动建表,无需运行。幂等可重跑(列已存在输出 SKIP 不报错)。

用法:
    cd backend
    python migrate_to_v1.4.2.py            # 默认 ./money.db
    python migrate_to_v1.4.2.py /path/db   # 指定库路径
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
    print(f"[v1.4.2 migration] target: {database_url}")
    engine = create_async_engine(database_url, echo=False)
    try:
        async with engine.begin() as conn:
            # 1. quick_templates 表是否存在(新库由应用自动建表,无需迁移)
            exists = (
                await conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='quick_templates'"
                    )
                )
            ).fetchone()
            if not exists:
                print("  [SKIP] quick_templates 表不存在(新库将由应用自动建表)")
                return 0

            # 2. kind 列缺失则补列;NOT NULL + DEFAULT 'manual' 使旧行一次性回填
            cols = [
                r[1]
                for r in (await conn.execute(text("PRAGMA table_info(quick_templates)"))).fetchall()
            ]
            if "kind" not in cols:
                await conn.execute(
                    text(
                        "ALTER TABLE quick_templates ADD COLUMN kind VARCHAR(20) "
                        "NOT NULL DEFAULT 'manual'"
                    )
                )
                res = await conn.execute(
                    text("SELECT COUNT(*) FROM quick_templates WHERE kind = 'manual'")
                )
                print(f"  [OK] 已为 quick_templates 添加 kind 列(旧行回填 manual: {res.scalar()})")
            else:
                print("  [SKIP] quick_templates.kind 已存在")
    finally:
        await engine.dispose()

    print("[v1.4.2 migration] 完成。")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(migrate(sys.argv)))
