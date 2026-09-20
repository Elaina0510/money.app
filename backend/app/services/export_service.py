"""Export service for CSV and SQL export."""

import csv
import io
from datetime import datetime
from typing import Any, cast

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget, BudgetCategory
from app.models.category import Category
from app.models.quick_template import QuickTemplate
from app.models.record import Record
from app.models.tag import Tag
from app.utils.money import round_money


async def export_csv(
    db: AsyncSession, user_id: int | None
) -> tuple[bytes, str]:
    """Export records as CSV with UTF-8 BOM."""
    from sqlalchemy import text

    # Fetch all categories for lookup
    cat_result = await db.execute(
        text("SELECT id, name FROM categories WHERE user_id = :uid"),
        {"uid": user_id},
    )
    categories = {row[0]: row[1] for row in cat_result.fetchall()}

    # Fetch all tags for lookup
    tag_result = await db.execute(
        text("SELECT id, name FROM tags WHERE user_id = :uid"),
        {"uid": user_id},
    )
    tags = {row[0]: row[1] for row in tag_result.fetchall()}

    # Query records
    rec_result = await db.execute(
        text(
            "SELECT amount, type, category_id, tag_id, consume_time, note "
            "FROM records WHERE user_id = :uid ORDER BY consume_time DESC"
        ),
        {"uid": user_id},
    )
    rows = rec_result.fetchall()

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["amount", "type", "category_name", "tag_name", "consume_time", "note"])

    for row in rows:
        amount, type_, cat_id, tag_id, consume_time, note = row
        category_name = categories.get(cat_id, "")
        tag_name = tags.get(tag_id, "") if tag_id else ""

        writer.writerow([
            round_money(amount),
            type_,
            category_name,
            tag_name,
            consume_time,
            note or "",
        ])

    # UTF-8 BOM
    csv_bytes = b"\xef\xbb\xbf" + output.getvalue().encode("utf-8")
    filename = f"money_export_{datetime.now().strftime('%Y%m%d')}.csv"
    return csv_bytes, filename


async def export_sql(
    db: AsyncSession, user_id: int | None
) -> tuple[bytes, str]:
    """Export user data as SQL backup."""
    lines: list[str] = []
    lines.append("-- Money App SQL Export")
    lines.append(f"-- Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"-- User ID: {user_id}")
    lines.append("")

    # Export categories (excluding presets)
    cat_query = (
        select(Category)
        .where(Category.user_id == user_id, Category.is_preset == 0)
        .order_by(Category.id)
    )
    cat_result = await db.exec(cat_query)
    categories = list(cat_result.all())

    if categories:
        lines.append("CREATE TABLE IF NOT EXISTS categories (")
        lines.append("    id INTEGER PRIMARY KEY AUTOINCREMENT,")
        lines.append("    name TEXT NOT NULL,")
        lines.append("    type TEXT NOT NULL,")
        lines.append("    icon TEXT NOT NULL,")
        lines.append("    sort_order INTEGER,")
        lines.append("    is_preset INTEGER DEFAULT 0,")
        lines.append("    user_id INTEGER,")
        lines.append("    deleted_at TEXT")
        lines.append(");")
        lines.append("")
        for cat in categories:
            lines.append(
                f"INSERT INTO categories (name, type, icon, sort_order, is_preset, user_id) "
                f"VALUES ('{_sql_escape(cat.name)}', '{cat.type}', '{_sql_escape(cat.icon)}', "
                f"{cat.sort_order or 0}, {cat.is_preset or 0}, {user_id});"
            )
        lines.append("")

    # Export tags
    tag_query = (
        select(Tag)
        .where(Tag.user_id == user_id)
        .order_by(Tag.id)
    )
    tag_result = await db.exec(tag_query)
    tags = list(tag_result.all())

    if tags:
        lines.append("CREATE TABLE IF NOT EXISTS tags (")
        lines.append("    id INTEGER PRIMARY KEY AUTOINCREMENT,")
        lines.append("    name TEXT NOT NULL,")
        lines.append("    category_id INTEGER,")
        lines.append("    user_id INTEGER,")
        lines.append("    deleted_at TEXT")
        lines.append(");")
        lines.append("")
        for tag in tags:
            lines.append(
                f"INSERT INTO tags (name, category_id, user_id) "
                f"VALUES ('{_sql_escape(tag.name)}', {tag.category_id or 'NULL'}, {user_id});"
            )
        lines.append("")

    # Export records
    rec_query = (
        select(Record).where(Record.user_id == user_id).order_by(Record.id)
    )
    rec_result = await db.exec(rec_query)
    records = list(rec_result.all())

    if records:
        lines.append("CREATE TABLE IF NOT EXISTS records (")
        lines.append("    id INTEGER PRIMARY KEY AUTOINCREMENT,")
        lines.append("    user_id INTEGER,")
        lines.append("    amount REAL NOT NULL,")
        lines.append("    type TEXT NOT NULL,")
        lines.append("    category_id INTEGER NOT NULL,")
        lines.append("    tag_id INTEGER,")
        lines.append("    consume_time TEXT NOT NULL,")
        lines.append("    note TEXT,")
        lines.append("    created_at TEXT NOT NULL,")
        lines.append("    updated_at TEXT NOT NULL")
        lines.append(");")
        lines.append("")
        for rec in records:
            note_val = f"'{_sql_escape(rec.note)}'" if rec.note else "NULL"
            tag_val = rec.tag_id if rec.tag_id else "NULL"
            lines.append(
                f"INSERT INTO records (user_id, amount, type, category_id, tag_id, "
                f"consume_time, note, created_at, updated_at) "
                f"VALUES ({rec.user_id}, {round_money(rec.amount)}, '{rec.type}', "
                f"{rec.category_id}, {tag_val}, "
                f"'{rec.consume_time}', {note_val}, "
                f"'{rec.created_at}', '{rec.updated_at}');"
            )
        lines.append("")

    # Export budgets（v1.4.3 M12 命名预算：budgets + budget_categories 两段）
    budget_query = (
        select(Budget).where(Budget.user_id == user_id).order_by(Budget.id)
    )
    budget_result = await db.exec(budget_query)
    budgets = list(budget_result.all())

    if budgets:
        # 预算行**带 id 导出**：budget_categories 需按原 budget_id 关联，
        # 导入侧靠「先读 old id → strip → 建行 → 记 map」的既有机制重映射
        lines.append("CREATE TABLE IF NOT EXISTS budgets (")
        lines.append("    id INTEGER PRIMARY KEY AUTOINCREMENT,")
        lines.append("    user_id INTEGER,")
        lines.append("    name TEXT NOT NULL,")
        lines.append("    month TEXT NOT NULL,")
        lines.append("    amount REAL NOT NULL,")
        lines.append("    scope_mode TEXT NOT NULL,")
        lines.append("    created_at TEXT,")
        lines.append("    updated_at TEXT")
        lines.append(");")
        lines.append("")
        for b in budgets:
            created = f"'{b.created_at}'" if b.created_at else "NULL"
            updated = f"'{b.updated_at}'" if b.updated_at else "NULL"
            lines.append(
                "INSERT INTO budgets (id, user_id, name, month, amount, scope_mode, "
                "created_at, updated_at) "
                f"VALUES ({b.id}, {b.user_id}, '{_sql_escape(b.name)}', '{b.month}', "
                f"{round_money(b.amount)}, '{b.scope_mode}', {created}, {updated});"
            )
        lines.append("")

        budget_ids = [int(b.id) for b in budgets if b.id is not None]
        links: list[BudgetCategory] = []
        if budget_ids:
            # cast(Any, ...)：SQLModel 类字段在 mypy 视角是普通 int 值，
            # 其 Core 表达式身份（in_/order_by）不可见；运行时即原对象。
            link_query = (
                select(BudgetCategory)
                .where(cast("Any", BudgetCategory.budget_id).in_(budget_ids))
                .order_by(cast("Any", BudgetCategory.id))
            )
            link_result = await db.exec(link_query)
            links = list(link_result.all())
        if links:
            # 关联行**双写 category_id + category_name**：categories 段不带 id、预设段
            # 根本不导出，导入侧的 old_id→new_id 映射对分类常常是空的，只给 id 就会
            # 整片丢关联（预算卡的覆盖范围静默清空）。名字兜底与 .db 路径同一规则
            # （M8 口径「同名即同一分类」）。
            linked_cat_ids = sorted({int(link.category_id) for link in links})
            name_rows = await db.exec(
                select(Category.id, Category.name).where(
                    cast("Any", Category.id).in_(linked_cat_ids)
                )
            )
            cat_names = {
                int(row[0]): str(row[1]) for row in name_rows.all() if row[0] is not None
            }
            lines.append("CREATE TABLE IF NOT EXISTS budget_categories (")
            lines.append("    id INTEGER PRIMARY KEY AUTOINCREMENT,")
            lines.append("    budget_id INTEGER NOT NULL,")
            lines.append("    category_id INTEGER NOT NULL,")
            lines.append("    category_name TEXT")
            lines.append(");")
            lines.append("")
            for link in links:
                lines.append(
                    "INSERT INTO budget_categories (id, budget_id, category_id,"
                    " category_name) VALUES "
                    f"({link.id}, {link.budget_id}, {link.category_id},"
                    f" '{_sql_escape(cat_names.get(int(link.category_id), ''))}');"
                )
            lines.append("")

    # Export quick templates
    # M6 隔离性核查：只导出 kind='manual' 的手动模板——auto_ignored 忽略行不得混入任何出口
    # （导入侧按手动模板建行，若导出忽略行会还原成幽灵手动模板；忽略名单不进备份属设计范围外）
    qt_query = (
        select(QuickTemplate)
        .where(QuickTemplate.user_id == user_id)
        .where(QuickTemplate.kind == "manual")
        .order_by(QuickTemplate.id)
    )
    qt_result = await db.exec(qt_query)
    templates = list(qt_result.all())

    if templates:
        lines.append("CREATE TABLE IF NOT EXISTS quick_templates (")
        lines.append("    id INTEGER PRIMARY KEY AUTOINCREMENT,")
        lines.append("    user_id INTEGER,")
        lines.append("    tag_id INTEGER,")
        lines.append("    category_id INTEGER,")
        lines.append("    type TEXT NOT NULL,")
        lines.append("    amount REAL NOT NULL,")
        lines.append("    created_at TEXT")
        lines.append(");")
        lines.append("")
        for qt in templates:
            tag_val = qt.tag_id if qt.tag_id else "NULL"
            cat_val = qt.category_id if qt.category_id else "NULL"
            created = f"'{qt.created_at}'" if qt.created_at else "NULL"
            lines.append(
                "INSERT INTO quick_templates (user_id, tag_id, category_id, "
                "type, amount, created_at) "
                f"VALUES ({qt.user_id}, {tag_val}, {cat_val}, '{qt.type}', "
                f"{round_money(qt.amount)}, {created});"
            )
        lines.append("")

    sql_text = "\n".join(lines) + "\n"
    sql_bytes = sql_text.encode("utf-8")
    filename = f"money_backup_{datetime.now().strftime('%Y%m%d')}.sql"
    return sql_bytes, filename


def _sql_escape(value: str) -> str:
    """Escape single quotes for SQL strings."""
    return value.replace("'", "''") if value else ""
