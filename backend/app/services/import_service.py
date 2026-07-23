"""Import service for CSV and SQL import."""

import csv
import io
import logging
import re
import sqlite3
import tempfile
from datetime import datetime
from typing import Any

import chardet
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.budget import Budget
from app.models.category import Category
from app.models.quick_template import QuickTemplate
from app.models.record import Record
from app.models.tag import Tag
from app.utils.cache import delete_cache, read_from_cache, save_to_cache
from app.utils.history import create_history_entry
from app.utils.money import round_money

logger = logging.getLogger(__name__)

# ── CSV Import ─────────────────────────────────────────────────────


def detect_and_decode(file_bytes: bytes) -> str:
    """Detect encoding: UTF-8 first, then chardet, fallback GBK."""
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        pass
    detected = chardet.detect(file_bytes)
    encoding = detected.get("encoding", "gbk")
    try:
        return file_bytes.decode(encoding)
    except (UnicodeDecodeError, TypeError):
        return file_bytes.decode("gbk", errors="replace")


def detect_csv_format(headers: list[str]) -> str:
    """Detect CSV format: native | cashew | unknown."""
    normalized = [h.strip().lower() for h in headers]
    native_headers = {"amount", "type", "category_name", "tag_name", "consume_time", "note"}
    if set(normalized) == native_headers:
        return "native"
    if "title" in normalized and "category name" in normalized:
        return "cashew"
    return "unknown"


CASHEW_COLUMN_MAP = {
    "title": "tag_name",
    "category name": "category_name",
    "amount": "amount",
    "income": "type",
    "note": "note",
    "date": "consume_time",
}

CASHEW_IGNORED_COLUMNS = {
    "subcategory name", "account", "currency", "wallet",
}


def convert_cashew_type(value: str) -> str:
    """Convert Cashew income field to type."""
    return "income" if value.strip().lower() == "true" else "expense"


def convert_cashew_amount(value: str) -> float:
    """Convert Cashew amount: take absolute value, round to 2 decimals."""
    try:
        return round_money(abs(float(value)))
    except (ValueError, TypeError):
        return 0.0


def convert_cashew_date(value: str) -> str:
    """Convert Cashew date: truncate to YYYY-MM-DD HH:MM."""
    return value[:16] if len(value) >= 16 else value


async def preview_csv(
    db: AsyncSession, file_bytes: bytes
) -> dict[str, Any]:
    """Preview CSV import: detect format, extract categories/tags, cache file."""
    content = detect_and_decode(file_bytes)
    reader = csv.reader(io.StringIO(content))
    headers = next(reader, None)
    if not headers:
        raise ValueError("CSV 文件为空")

    format_type = detect_csv_format(headers)
    if format_type == "unknown":
        raise ValueError("无法识别的 CSV 格式")

    # Build column index lookup
    normalized_headers = [h.strip().lower() for h in headers]

    if format_type == "native":
        cat_idx = normalized_headers.index("category_name")
        tag_idx = normalized_headers.index("tag_name")
    else:  # cashew
        cat_idx = normalized_headers.index("category name")
        tag_idx = normalized_headers.index("title")

    # Parse rows
    categories_in_file: set[str] = set()
    tags_in_file: set[str] = set()
    row_count = 0

    for row in reader:
        if not row or all(cell.strip() == "" for cell in row):
            continue
        row_count += 1

        cat_name = row[cat_idx].strip() if len(row) > cat_idx else ""
        tag_name = row[tag_idx].strip() if len(row) > tag_idx else ""

        if cat_name:
            categories_in_file.add(cat_name)
        if tag_name:
            tags_in_file.add(tag_name)

    # Cache the file
    cache_id = save_to_cache(file_bytes, ".csv")

    return {
        "format": format_type,
        "row_count": row_count,
        "categories_in_file": sorted(categories_in_file),
        "tags_in_file": sorted(tags_in_file),
        "cache_id": cache_id,
    }


async def import_csv_data(
    db: AsyncSession,
    user_id: int | None,
    cache_id: str,
    format_type: str,
    category_mapping: dict[str, Any],
    tag_mapping: dict[str, Any],
) -> dict[str, Any]:
    """Import CSV data with mapping."""
    file_bytes = read_from_cache(cache_id, ".csv")
    content = detect_and_decode(file_bytes)
    reader = csv.reader(io.StringIO(content))
    headers = next(reader, None)

    # Normalize headers
    normalized = [h.strip().lower() for h in headers]

    imported_count = 0
    skipped_count = 0
    imported_records: list[dict[str, Any]] = []

    for row in reader:
        if not row or all(cell.strip() == "" for cell in row):
            continue

        # Parse row based on format
        if format_type == "native":
            amount_str, type_str, cat_name, tag_name, consume_time, note = (
                _parse_native_row(row)
            )
        else:  # cashew
            amount_str, type_str, cat_name, tag_name, consume_time, note = (
                _parse_cashew_row(row, normalized)
            )

        # Validate required fields
        try:
            amount = round_money(float(amount_str))
        except (ValueError, TypeError):
            skipped_count += 1
            continue

        if type_str not in ("income", "expense"):
            skipped_count += 1
            continue

        if not consume_time:
            skipped_count += 1
            continue

        # Resolve category
        cat_mapping = category_mapping.get(cat_name)
        if not cat_mapping:
            skipped_count += 1
            continue

        if cat_mapping.get("action") == "create":
            category = Category(
                name=cat_name,
                type=cat_mapping.get("type", "expense"),
                icon="mdi-circle",
                user_id=user_id,
            )
            db.add(category)
            await db.flush()
            category_id = category.id
        else:
            category_id = cat_mapping.get("target_id")
            if not category_id:
                skipped_count += 1
                continue

        # Resolve tag
        tag_id = None
        if tag_name:
            t_mapping = tag_mapping.get(tag_name)
            if t_mapping:
                if t_mapping.get("action") == "create":
                    tag = Tag(
                        name=tag_name,
                        category_id=t_mapping.get("category_id"),
                        user_id=user_id,
                    )
                    db.add(tag)
                    await db.flush()
                    tag_id = tag.id
                else:
                    tag_id = t_mapping.get("target_id")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = Record(
            amount=amount,
            type=type_str,
            category_id=category_id,
            tag_id=tag_id,
            consume_time=consume_time,
            note=note or None,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        db.add(record)
        await db.flush()
        imported_records.append({
            "id": record.id,
            "amount": record.amount,
            "type": record.type,
            "category_id": record.category_id,
            "tag_id": record.tag_id,
            "consume_time": record.consume_time,
            "note": record.note,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        })
        imported_count += 1

    # Write history
    if imported_records:
        await create_history_entry(
            db, user_id, "csv_import",
            f"CSV 导入 {imported_count} 条账单",
            snapshot_after=imported_records,
        )

    await db.commit()
    delete_cache(cache_id, ".csv")

    logger.info(
        "csv_import done user=%s imported=%d skipped=%d", user_id, imported_count, skipped_count
    )

    return {
        "imported_count": imported_count,
        "skipped_count": skipped_count,
    }


def _parse_native_row(row: list[str]) -> tuple:
    """Parse a native format CSV row."""
    amount = row[0].strip() if len(row) > 0 else ""
    type_ = row[1].strip() if len(row) > 1 else ""
    cat_name = row[2].strip() if len(row) > 2 else ""
    tag_name = row[3].strip() if len(row) > 3 else ""
    consume_time = row[4].strip() if len(row) > 4 else ""
    note = row[5].strip() if len(row) > 5 else ""
    return amount, type_, cat_name, tag_name, consume_time, note


def _parse_cashew_row(
    row: list[str], headers: list[str]
) -> tuple:
    """Parse a Cashew format CSV row."""
    data = {}
    for i, header in enumerate(headers):
        if i < len(row):
            data[header] = row[i].strip()

    amount = convert_cashew_amount(data.get("amount", "0"))
    type_ = convert_cashew_type(data.get("income", "false"))
    cat_name = data.get("category name", "")
    tag_name = data.get("title", "")
    consume_time = convert_cashew_date(data.get("date", ""))
    note = data.get("note", "")
    return str(amount), type_, cat_name, tag_name, consume_time, note


# ── SQL Import ─────────────────────────────────────────────────────


def detect_sql_format(file_bytes: bytes) -> str:
    """Detect SQL format: text_sql | sqlite_binary | unknown."""
    if file_bytes[:16] == b"SQLite format 3\x00":
        return "sqlite_binary"
    # Check for text SQL markers
    try:
        text = file_bytes[:500].decode("utf-8", errors="ignore").strip().upper()
        if any(text.startswith(kw) for kw in ("CREATE", "INSERT", "--", "BEGIN", "PRAGMA")):
            return "text_sql"
    except Exception:
        pass
    return "unknown"


def detect_cashew_sqlite(conn: sqlite3.Connection) -> bool:
    """Detect if a SQLite database is from Cashew app."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "transactions" not in tables or "categories" not in tables:
        return False
    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(transactions)"
        ).fetchall()
    }
    return (
        "category_fk" in columns
        and "income" in columns
        and "date_created" in columns
    )


def strip_id_from_insert(sql_statement: str) -> str:
    """Remove id column from INSERT statement if present."""
    pattern = r"INSERT\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\((.+)\)"
    match = re.match(pattern, sql_statement, re.IGNORECASE | re.DOTALL)
    if not match:
        return sql_statement
    table, columns_str, values_str = match.groups()
    columns = [c.strip() for c in columns_str.split(",")]
    if "id" not in columns:
        return sql_statement
    id_index = columns.index("id")
    values = next(
        csv.reader(io.StringIO(values_str), skipinitialspace=True)
    )
    columns.pop(id_index)
    values.pop(id_index)
    return (
        f"INSERT INTO {table} ({', '.join(columns)}) "
        f"VALUES ({', '.join(values)})"
    )


def parse_text_sql(file_content: str) -> dict[str, Any]:
    """Parse text SQL file and extract table data for preview."""
    tables: dict[str, dict[str, Any]] = {}
    statements: list[str] = []
    categories_in_file: list[str] = []
    tags_in_file: list[str] = []

    # Merge multi-line statements
    current_stmt = ""
    for line in file_content.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current_stmt += " " + stripped
        if stripped.endswith(";"):
            stmt = current_stmt.strip()
            statements.append(stmt)
            current_stmt = ""

            # Extract table info
            upper = stmt.upper()
            if upper.startswith("INSERT"):
                m = re.match(
                    r"INSERT\s+INTO\s+(\w+)", stmt, re.IGNORECASE
                )
                if m:
                    table_name = m.group(1)
                    if table_name not in tables:
                        tables[table_name] = {"count": 0, "sample": []}
                    tables[table_name]["count"] += 1

                    # Extract category/tag names for mapping
                    values = _extract_values(stmt)
                    if table_name == "categories" and values:
                        name = _unquote(values.get("name", ""))
                        if name:
                            categories_in_file.append(name)
                    elif table_name == "tags" and values:
                        name = _unquote(values.get("name", ""))
                        if name:
                            tags_in_file.append(name)
            elif upper.startswith("CREATE TABLE"):
                m = re.match(
                    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)",
                    stmt,
                    re.IGNORECASE,
                )
                if m:
                    table_name = m.group(1)
                    if table_name not in tables:
                        tables[table_name] = {"count": 0, "sample": []}

    return {
        "tables": tables,
        "statements": statements,
        "categories_in_file": categories_in_file,
        "tags_in_file": tags_in_file,
    }


def parse_sqlite_file(file_bytes: bytes) -> dict[str, Any]:
    """Parse SQLite file and extract table data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        conn = sqlite3.connect(tmp_path)
        is_cashew = detect_cashew_sqlite(conn)

        tables: dict[str, dict[str, Any]] = {}
        categories_in_file: list[str] = []
        tags_in_file: list[str] = []

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        table_names = [row[0] for row in cursor.fetchall()]

        for table_name in table_names:
            cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            count = cursor.fetchone()[0]
            tables[table_name] = {"count": count, "sample": []}

            # Get sample rows
            cursor = conn.execute(f"SELECT * FROM [{table_name}] LIMIT 3")
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                tables[table_name]["sample"].append(
                    dict(zip(columns, row))
                )

        # Extract category and tag names for mapping
        if is_cashew:
            # Cashew: categories from 'categories' table, tags from transaction 'name'
            try:
                rows = conn.execute("SELECT name FROM categories").fetchall()
                categories_in_file = [r[0] for r in rows if r[0]]
            except sqlite3.OperationalError:
                pass
            try:
                rows = conn.execute(
                    "SELECT DISTINCT name FROM transactions WHERE name != ''"
                ).fetchall()
                tags_in_file = [r[0] for r in rows if r[0]]
            except sqlite3.OperationalError:
                pass
        else:
            # Standard SQLite
            try:
                rows = conn.execute("SELECT name FROM categories").fetchall()
                categories_in_file = [r[0] for r in rows if r[0]]
            except sqlite3.OperationalError:
                pass
            try:
                rows = conn.execute("SELECT name FROM tags").fetchall()
                tags_in_file = [r[0] for r in rows if r[0]]
            except sqlite3.OperationalError:
                pass

        conn.close()
        return {
            "tables": tables,
            "is_cashew": is_cashew,
            "categories_in_file": categories_in_file,
            "tags_in_file": tags_in_file,
        }
    finally:
        import os

        os.unlink(tmp_path)


async def preview_sql(
    db: AsyncSession, file_bytes: bytes
) -> dict[str, Any]:
    """Preview SQL import."""
    format_type = detect_sql_format(file_bytes)
    if format_type == "unknown":
        raise ValueError("不支持的文件格式")

    is_third_party = False
    categories_in_file: list[str] = []
    tags_in_file: list[str] = []

    if format_type == "text_sql":
        content = file_bytes.decode("utf-8", errors="replace")
        parsed = parse_text_sql(content)
        tables_info = parsed["tables"]
        categories_in_file = parsed.get("categories_in_file", [])
        tags_in_file = parsed.get("tags_in_file", [])
    else:  # sqlite_binary
        parsed = parse_sqlite_file(file_bytes)
        tables_info = parsed["tables"]
        is_third_party = parsed.get("is_cashew", False)
        categories_in_file = parsed.get("categories_in_file", [])
        tags_in_file = parsed.get("tags_in_file", [])

    # Cache the file
    suffix = ".sql" if format_type == "text_sql" else ".db"
    cache_id = save_to_cache(file_bytes, suffix)

    return {
        "format": format_type,
        "is_third_party": is_third_party,
        "tables": tables_info,
        "cache_id": cache_id,
        "categories_in_file": categories_in_file,
        "tags_in_file": tags_in_file,
    }


async def import_sql_data(
    db: AsyncSession,
    user_id: int | None,
    cache_id: str,
    format_type: str,
    is_third_party: bool = False,
    category_mapping: dict[str, Any] | None = None,
    tag_mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import SQL data within a transaction."""
    suffix = ".sql" if format_type == "text_sql" else ".db"
    file_bytes = read_from_cache(cache_id, suffix)

    try:
        logger.info(
            "sql_import start user=%s format=%s third_party=%s",
            user_id, format_type, is_third_party,
        )
        if format_type == "text_sql":
            result = await _import_text_sql(
                db, user_id, file_bytes, category_mapping, tag_mapping
            )
        else:
            result = await _import_sqlite_binary(
                db, user_id, file_bytes, is_third_party,
                category_mapping, tag_mapping
            )

        # Write history
        await create_history_entry(
            db, user_id, "sql_import",
            f"SQL 导入 {result.get('records_imported', 0)} 条账单",
            snapshot_after=result.get("imported_records", []),
        )

        await db.commit()
        delete_cache(cache_id, suffix)
        logger.info(
            "sql_import done user=%s records=%d",
            user_id, result.get("records_imported", 0),
        )
        return result
    except Exception:
        await db.rollback()
        logger.exception("sql_import failed user=%s", user_id)
        raise


async def _import_text_sql(
    db: AsyncSession,
    user_id: int | None,
    file_bytes: bytes,
    category_mapping: dict[str, Any] | None = None,
    tag_mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import from text SQL file."""
    content = file_bytes.decode("utf-8", errors="replace")
    parsed = parse_text_sql(content)
    statements = parsed["statements"]

    records_imported = 0
    imported_records: list[dict[str, Any]] = []
    category_map: dict[int, int] = {}  # old_id -> new_id
    tag_map: dict[int, int] = {}

    for stmt in statements:
        upper = stmt.upper().strip()

        if upper.startswith("CREATE TABLE"):
            continue  # Skip CREATE TABLE

        if not upper.startswith("INSERT"):
            continue

        # Extract table name and old id before stripping
        m = re.match(r"INSERT\s+INTO\s+(\w+)", stmt, re.IGNORECASE)
        if not m:
            continue
        table_name = m.group(1)

        # Get old id from values if present
        values = _extract_values(stmt)
        old_id = _parse_int(values.get("id"))

        # Strip id if present
        stmt = strip_id_from_insert(stmt)

        if table_name == "categories":
            new_id = await _import_category_stmt(db, user_id, stmt)
            if new_id:
                records_imported += 1
                if old_id:
                    category_map[old_id] = new_id
        elif table_name == "tags":
            new_id = await _import_tag_stmt(db, user_id, stmt, category_map)
            if new_id:
                records_imported += 1
                if old_id:
                    tag_map[old_id] = new_id
        elif table_name == "records":
            record_data = await _import_record_stmt(
                db, user_id, stmt, category_map, tag_map
            )
            if record_data:
                imported_records.append(record_data)
                records_imported += 1
        elif table_name == "budgets":
            await _import_budget_stmt(db, user_id, stmt, category_map)
            records_imported += 1
        elif table_name == "quick_templates":
            await _import_quick_template_stmt(
                db, user_id, stmt, category_map, tag_map
            )
            records_imported += 1

    return {
        "records_imported": len(imported_records),
        "total_imported": records_imported,
        "imported_records": imported_records,
    }


async def _import_category_stmt(
    db: AsyncSession, user_id: int | None, stmt: str
) -> int | None:
    """Import a category from an INSERT statement."""
    values = _extract_values(stmt)
    if not values:
        return None

    # Parse category fields
    name = _unquote(values.get("name", ""))
    cat_type = _unquote(values.get("type", "expense"))
    icon = _unquote(values.get("icon", "mdi-circle"))

    # Check for existing category
    existing = await db.exec(
        select(Category).where(
            Category.name == name,
            Category.type == cat_type,
            Category.user_id == user_id,
        )
    )
    existing_cat = existing.first()
    if existing_cat:
        return existing_cat.id

    category = Category(
        name=name,
        type=cat_type,
        icon=icon,
        user_id=user_id,
    )
    db.add(category)
    await db.flush()
    return category.id


async def _import_tag_stmt(
    db: AsyncSession,
    user_id: int | None,
    stmt: str,
    category_map: dict[int, int] | None = None,
) -> int | None:
    """Import a tag from an INSERT statement."""
    values = _extract_values(stmt)
    if not values:
        return None

    name = _unquote(values.get("name", ""))
    category_id = _parse_int(values.get("category_id"))

    # Map old category ID to new ID
    if category_map and category_id:
        category_id = category_map.get(category_id, category_id)

    # Check for existing tag
    existing = await db.exec(
        select(Tag).where(
            Tag.name == name,
            Tag.user_id == user_id,
        )
    )
    existing_tag = existing.first()
    if existing_tag:
        return existing_tag.id

    tag = Tag(
        name=name,
        category_id=category_id,
        user_id=user_id,
    )
    db.add(tag)
    await db.flush()
    return tag.id


async def _import_record_stmt(
    db: AsyncSession,
    user_id: int | None,
    stmt: str,
    category_map: dict[int, int] | None = None,
    tag_map: dict[int, int] | None = None,
) -> dict[str, Any] | None:
    """Import a record from an INSERT statement."""
    values = _extract_values(stmt)
    if not values:
        return None

    amount = _parse_float(values.get("amount"))
    rec_type = _unquote(values.get("type", ""))
    category_id = _parse_int(values.get("category_id"))
    tag_id = _parse_int(values.get("tag_id"))
    consume_time = _unquote(values.get("consume_time", ""))
    note = _unquote(values.get("note", ""))
    created_at = _unquote(values.get("created_at", ""))
    updated_at = _unquote(values.get("updated_at", ""))

    # Map old IDs to new IDs
    if category_map and category_id:
        category_id = category_map.get(category_id, category_id)
    if tag_map and tag_id:
        tag_id = tag_map.get(tag_id, tag_id)

    if not amount or rec_type not in ("income", "expense"):
        return None
    if not category_id or not consume_time:
        return None

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = Record(
        amount=amount,
        type=rec_type,
        category_id=category_id,
        tag_id=tag_id,
        consume_time=consume_time,
        note=note or None,
        user_id=user_id,
        created_at=created_at or now,
        updated_at=updated_at or now,
    )
    db.add(record)
    await db.flush()
    return {
        "id": record.id,
        "amount": record.amount,
        "type": record.type,
        "category_id": record.category_id,
        "tag_id": record.tag_id,
        "consume_time": record.consume_time,
        "note": record.note,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


async def _import_budget_stmt(
    db: AsyncSession,
    user_id: int | None,
    stmt: str,
    category_map: dict[int, int] | None = None,
) -> None:
    """Import a budget from an INSERT statement."""
    values = _extract_values(stmt)
    if not values:
        return

    category_id = _parse_int(values.get("category_id"))
    amount = _parse_float(values.get("amount"))
    period = _unquote(values.get("period", "monthly"))

    # Map old category ID to new ID
    if category_map and category_id:
        category_id = category_map.get(category_id, category_id)

    if not amount:
        return

    budget = Budget(
        user_id=user_id,
        category_id=category_id,
        amount=amount,
        period=period,
    )
    db.add(budget)
    await db.flush()


async def _import_quick_template_stmt(
    db: AsyncSession,
    user_id: int | None,
    stmt: str,
    category_map: dict[int, int] | None = None,
    tag_map: dict[int, int] | None = None,
) -> None:
    """Import a quick template from an INSERT statement."""
    values = _extract_values(stmt)
    if not values:
        return

    tag_id = _parse_int(values.get("tag_id"))
    category_id = _parse_int(values.get("category_id"))
    qt_type = _unquote(values.get("type", "expense"))
    amount = _parse_float(values.get("amount"))

    # Map old IDs to new IDs
    if category_map and category_id:
        category_id = category_map.get(category_id, category_id)
    if tag_map and tag_id:
        tag_id = tag_map.get(tag_id, tag_id)

    if not amount:
        return

    qt = QuickTemplate(
        user_id=user_id,
        tag_id=tag_id,
        category_id=category_id,
        type=qt_type,
        amount=amount,
    )
    db.add(qt)
    await db.flush()


async def _import_sqlite_binary(
    db: AsyncSession,
    user_id: int | None,
    file_bytes: bytes,
    is_third_party: bool,
    category_mapping: dict[str, Any] | None = None,
    tag_mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import from SQLite binary file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        conn = sqlite3.connect(tmp_path)
        conn.row_factory = sqlite3.Row

        records_imported = 0
        imported_records: list[dict[str, Any]] = []

        if is_third_party:
            # Cashew format
            result = await _import_cashew_sqlite(
                db, user_id, conn, category_mapping, tag_mapping
            )
            conn.close()
            return result

        # Standard SQLite import
        # Import categories
        try:
            rows = conn.execute("SELECT * FROM categories").fetchall()
            for row in rows:
                name = row["name"]
                cat_type = row["type"]
                icon = row["icon"]

                existing = await db.exec(
                    select(Category).where(
                        Category.name == name,
                        Category.type == cat_type,
                        Category.user_id == user_id,
                    )
                )
                if not existing.first():
                    category = Category(
                        name=name,
                        type=cat_type,
                        icon=icon,
                        user_id=user_id,
                    )
                    db.add(category)
                    await db.flush()
        except sqlite3.OperationalError:
            pass

        # Import tags
        try:
            rows = conn.execute("SELECT * FROM tags").fetchall()
            for row in rows:
                name = row["name"]
                category_id = row["category_id"] if "category_id" in row.keys() else None

                existing = await db.exec(
                    select(Tag).where(
                        Tag.name == name,
                        Tag.user_id == user_id,
                    )
                )
                if not existing.first():
                    tag = Tag(
                        name=name,
                        category_id=category_id,
                        user_id=user_id,
                    )
                    db.add(tag)
                    await db.flush()
        except sqlite3.OperationalError:
            pass

        # Import records
        try:
            rows = conn.execute("SELECT * FROM records").fetchall()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for row in rows:
                amount = row["amount"]
                rec_type = row["type"]
                category_id = row["category_id"]
                tag_id = row["tag_id"] if "tag_id" in row.keys() else None
                consume_time = row["consume_time"]
                note = row["note"] if "note" in row.keys() else None
                created_at = row["created_at"] if "created_at" in row.keys() else now
                updated_at = row["updated_at"] if "updated_at" in row.keys() else now

                if not amount or rec_type not in ("income", "expense"):
                    continue
                if not category_id or not consume_time:
                    continue

                record = Record(
                    amount=round_money(amount),
                    type=rec_type,
                    category_id=category_id,
                    tag_id=tag_id,
                    consume_time=consume_time,
                    note=note,
                    user_id=user_id,
                    created_at=created_at or now,
                    updated_at=updated_at or now,
                )
                db.add(record)
                await db.flush()
                imported_records.append({
                    "id": record.id,
                    "amount": record.amount,
                    "type": record.type,
                    "category_id": record.category_id,
                    "tag_id": record.tag_id,
                    "consume_time": record.consume_time,
                    "note": record.note,
                    "created_at": record.created_at,
                    "updated_at": record.updated_at,
                })
                records_imported += 1
        except sqlite3.OperationalError:
            pass

        # Import budgets
        try:
            rows = conn.execute("SELECT * FROM budgets").fetchall()
            for row in rows:
                budget = Budget(
                    user_id=user_id,
                    category_id=row["category_id"] if "category_id" in row.keys() else None,
                    amount=round_money(row["amount"]),
                    period=row["period"],
                )
                db.add(budget)
                await db.flush()
        except sqlite3.OperationalError:
            pass

        # Import quick templates
        try:
            rows = conn.execute("SELECT * FROM quick_templates").fetchall()
            for row in rows:
                qt = QuickTemplate(
                    user_id=user_id,
                    tag_id=row["tag_id"] if "tag_id" in row.keys() else None,
                    category_id=row["category_id"] if "category_id" in row.keys() else None,
                    type=row["type"],
                    amount=round_money(row["amount"]),
                )
                db.add(qt)
                await db.flush()
        except sqlite3.OperationalError:
            pass

        conn.close()
        return {
            "records_imported": records_imported,
            "total_imported": records_imported,
            "imported_records": imported_records,
        }
    finally:
        import os

        os.unlink(tmp_path)


async def _import_cashew_sqlite(
    db: AsyncSession,
    user_id: int | None,
    conn: sqlite3.Connection,
    category_mapping: dict[str, Any] | None = None,
    tag_mapping: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Import from Cashew SQLite database."""
    # Build category mapping: cashew_id -> category_name
    # Cashew uses 'category_pk' as primary key
    cashew_categories: dict[str, str] = {}
    rows = conn.execute("SELECT * FROM categories").fetchall()
    for row in rows:
        pk = str(row["category_pk"])
        cashew_categories[pk] = row["name"]

    records_imported = 0
    imported_records: list[dict[str, Any]] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Import transactions
    rows = conn.execute("SELECT * FROM transactions").fetchall()
    for row in rows:
        # Map fields
        amount = round_money(abs(float(row["amount"]))) if row["amount"] else 0
        rec_type = "income" if row["income"] == 1 else "expense"
        tag_name = row["name"] if row["name"] else ""
        note = row["note"] if row["note"] else ""

        # Convert Unix timestamp (Cashew stores in seconds)
        date_created = row["date_created"]
        if isinstance(date_created, (int, float)):
            # Handle both seconds and milliseconds
            if date_created > 1e12:
                date_created = date_created / 1000
            consume_time = datetime.fromtimestamp(date_created).strftime(
                "%Y-%m-%d %H:%M"
            )
        else:
            consume_time = str(date_created)[:16]

        # Resolve category
        cashew_cat_id = str(row["category_fk"])
        cat_name = cashew_categories.get(cashew_cat_id, "")
        category_id = None

        if cat_name:
            # Check mapping first
            if category_mapping and cat_name in category_mapping:
                cat_map = category_mapping[cat_name]
                if cat_map.get("action") == "create":
                    new_cat = Category(
                        name=cat_name,
                        type=cat_map.get("type", rec_type),
                        icon="mdi-circle",
                        user_id=user_id,
                    )
                    db.add(new_cat)
                    await db.flush()
                    category_id = new_cat.id
                else:
                    category_id = cat_map.get("target_id")
            else:
                # Auto-match by name
                existing = await db.exec(
                    select(Category).where(
                        Category.name == cat_name,
                        Category.user_id == user_id,
                    )
                )
                cat = existing.first()
                if cat:
                    category_id = cat.id
                else:
                    new_cat = Category(
                        name=cat_name,
                        type=rec_type,
                        icon="mdi-circle",
                        user_id=user_id,
                    )
                    db.add(new_cat)
                    await db.flush()
                    category_id = new_cat.id

        if not category_id:
            continue

        # Resolve tag
        tag_id = None
        if tag_name:
            # Check mapping first
            if tag_mapping and tag_name in tag_mapping:
                t_map = tag_mapping[tag_name]
                if t_map.get("action") == "create":
                    new_tag = Tag(
                        name=tag_name,
                        category_id=t_map.get("category_id", category_id),
                        user_id=user_id,
                    )
                    db.add(new_tag)
                    await db.flush()
                    tag_id = new_tag.id
                else:
                    tag_id = t_map.get("target_id")
            else:
                # Auto-match by name
                existing = await db.exec(
                    select(Tag).where(
                        Tag.name == tag_name,
                        Tag.user_id == user_id,
                    )
                )
                tag = existing.first()
                if tag:
                    tag_id = tag.id
                else:
                    new_tag = Tag(
                        name=tag_name,
                        category_id=category_id,
                        user_id=user_id,
                    )
                    db.add(new_tag)
                    await db.flush()
                    tag_id = new_tag.id

        record = Record(
            amount=amount,
            type=rec_type,
            category_id=category_id,
            tag_id=tag_id,
            consume_time=consume_time,
            note=note or None,
            user_id=user_id,
            created_at=now,
            updated_at=None,
        )
        db.add(record)
        await db.flush()
        imported_records.append({
            "id": record.id,
            "amount": record.amount,
            "type": record.type,
            "category_id": record.category_id,
            "tag_id": record.tag_id,
            "consume_time": record.consume_time,
            "note": record.note,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        })
        records_imported += 1

    conn.close()
    return {
        "records_imported": records_imported,
        "total_imported": records_imported,
        "imported_records": imported_records,
    }


def _extract_values(stmt: str) -> dict[str, str]:
    """Extract column=value pairs from an INSERT statement."""
    pattern = r"INSERT\s+INTO\s+\w+\s*\(([^)]+)\)\s*VALUES\s*\((.+)\)"
    match = re.match(pattern, stmt, re.IGNORECASE | re.DOTALL)
    if not match:
        return {}

    columns_str, values_str = match.groups()
    columns = [c.strip() for c in columns_str.split(",")]
    values = list(csv.reader(io.StringIO(values_str), skipinitialspace=True))

    if not values:
        return {}

    result = {}
    for i, col in enumerate(columns):
        if i < len(values[0]):
            result[col] = values[0][i].strip()
    return result


def _unquote(value: str) -> str:
    """Remove surrounding single quotes from a value."""
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def _parse_int(value: str | None) -> int | None:
    """Parse an integer value, returning None for NULL."""
    if not value or value.upper() == "NULL":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _parse_float(value: str | None) -> float | None:
    """Parse a float value, returning None for NULL."""
    if not value or value.upper() == "NULL":
        return None
    try:
        return round_money(float(value))
    except (ValueError, TypeError):
        return None
