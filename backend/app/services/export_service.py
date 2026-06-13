"""Export service for CSV and SQL export."""

import csv
import io
from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget
from app.models.category import Category
from app.models.quick_template import QuickTemplate
from app.models.record import Record
from app.models.tag import Tag


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
            amount,
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
                f"VALUES ({rec.user_id}, {rec.amount}, '{rec.type}', "
                f"{rec.category_id}, {tag_val}, "
                f"'{rec.consume_time}', {note_val}, "
                f"'{rec.created_at}', '{rec.updated_at}');"
            )
        lines.append("")

    # Export budgets
    budget_query = (
        select(Budget).where(Budget.user_id == user_id).order_by(Budget.id)
    )
    budget_result = await db.exec(budget_query)
    budgets = list(budget_result.all())

    if budgets:
        lines.append("CREATE TABLE IF NOT EXISTS budgets (")
        lines.append("    id INTEGER PRIMARY KEY AUTOINCREMENT,")
        lines.append("    user_id INTEGER,")
        lines.append("    category_id INTEGER,")
        lines.append("    amount REAL NOT NULL,")
        lines.append("    period TEXT NOT NULL,")
        lines.append("    created_at TEXT,")
        lines.append("    updated_at TEXT")
        lines.append(");")
        lines.append("")
        for b in budgets:
            cat_val = b.category_id if b.category_id else "NULL"
            created = f"'{b.created_at}'" if b.created_at else "NULL"
            updated = f"'{b.updated_at}'" if b.updated_at else "NULL"
            lines.append(
                "INSERT INTO budgets (user_id, category_id, amount, period, "
                "created_at, updated_at) "
                f"VALUES ({b.user_id}, {cat_val}, {b.amount}, '{b.period}', "
                f"{created}, {updated});"
            )
        lines.append("")

    # Export quick templates
    qt_query = (
        select(QuickTemplate)
        .where(QuickTemplate.user_id == user_id)
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
                f"{qt.amount}, {created});"
            )
        lines.append("")

    sql_text = "\n".join(lines) + "\n"
    sql_bytes = sql_text.encode("utf-8")
    filename = f"money_backup_{datetime.now().strftime('%Y%m%d')}.sql"
    return sql_bytes, filename


def _sql_escape(value: str) -> str:
    """Escape single quotes for SQL strings."""
    return value.replace("'", "''") if value else ""
