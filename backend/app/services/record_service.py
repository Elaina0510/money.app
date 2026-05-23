"""Record business logic."""

from datetime import datetime
from typing import Any

from sqlmodel import select, func, or_
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.record import Record
from app.models.tag import Tag
from app.models.category import Category
from app.models.attachment import Attachment
from app.schemas.record import RecordCreate, RecordUpdate
from app.utils.response import Code


async def create_record(
    db: AsyncSession, data: RecordCreate
) -> Record:
    """Create a new record with a single tag."""
    # Validate category exists
    category = await db.get(Category, data.category_id)
    if not category:
        raise ValueError("分类不存在")

    # Validate tag exists if tag_id is provided
    if data.tag_id:
        tag = await db.get(Tag, data.tag_id)
        if not tag:
            raise ValueError("标签不存在")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    consume_time = data.consume_time or datetime.now().strftime("%Y-%m-%d %H:%M")

    record = Record(
        amount=data.amount,
        type=data.type,
        category_id=data.category_id,
        tag_id=data.tag_id,
        consume_time=consume_time,
        note=data.note,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_records(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    start_date: str | None = None,
    end_date: str | None = None,
    category_id: int | None = None,
    type_filter: str | None = None,
    tag_id: int | None = None,
    keyword: str | None = None,
    sort_by: str = "consume_time",
    sort_order: str = "desc",
) -> dict[str, Any]:
    """Get paginated records with optional filters."""
    query = select(Record)
    count_query = select(func.count(Record.id))

    # Apply filters
    if start_date:
        query = query.where(Record.consume_time >= start_date)
        count_query = count_query.where(Record.consume_time >= start_date)
    if end_date:
        # Append 23:59 to end_date if it's just a date (YYYY-MM-DD)
        end_filter = end_date + " 23:59" if len(end_date) <= 10 else end_date
        query = query.where(Record.consume_time <= end_filter)
        count_query = count_query.where(Record.consume_time <= end_filter)
    if category_id:
        query = query.where(Record.category_id == category_id)
        count_query = count_query.where(Record.category_id == category_id)
    if type_filter:
        query = query.where(Record.type == type_filter)
        count_query = count_query.where(Record.type == type_filter)
    if tag_id:
        query = query.where(Record.tag_id == tag_id)
        count_query = count_query.where(Record.tag_id == tag_id)
    if keyword:
        # Search in note field
        query = query.where(Record.note.contains(keyword))
        count_query = count_query.where(Record.note.contains(keyword))

    # Get total count
    count_result = await db.exec(count_query)
    total = count_result.one()

    # Apply sorting — 使用白名单防止意外的属性注入
    VALID_SORT_BY = {"consume_time", "amount", "created_at", "updated_at"}
    if sort_by not in VALID_SORT_BY:
        sort_by = "consume_time"
    VALID_SORT_ORDER = {"asc", "desc"}
    if sort_order not in VALID_SORT_ORDER:
        sort_order = "desc"

    sort_column = getattr(Record, sort_by, Record.consume_time)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.exec(query)
    records = list(result.all())

    # Enrich records with category names, tag, and attachments
    items = []
    for record in records:
        items.append(await _enrich_record(db, record))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


async def get_record(db: AsyncSession, record_id: int) -> dict[str, Any] | None:
    """Get a single record with full details."""
    record = await db.get(Record, record_id)
    if not record:
        return None
    return await _enrich_record(db, record)


async def update_record(
    db: AsyncSession, record_id: int, data: RecordUpdate
) -> dict[str, Any] | None:
    """Update an existing record."""
    record = await db.get(Record, record_id)
    if not record:
        return None

    update_data = data.model_dump(exclude_unset=True)

    # Validate tag exists if tag_id is provided
    if "tag_id" in update_data and update_data["tag_id"] is not None:
        tag = await db.get(Tag, update_data["tag_id"])
        if not tag:
            raise ValueError("标签不存在")

    for key, value in update_data.items():
        setattr(record, key, value)

    record.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    await db.commit()
    await db.refresh(record)
    return await _enrich_record(db, record)


async def delete_record(db: AsyncSession, record_id: int) -> bool:
    """Delete a record. Returns True if deleted, False if not found."""
    record = await db.get(Record, record_id)
    if not record:
        return False
    await db.delete(record)
    await db.commit()
    return True


async def batch_delete_records(db: AsyncSession, ids: list[int]) -> int:
    """Delete multiple records. Returns the number deleted."""
    count = 0
    for rid in ids:
        record = await db.get(Record, rid)
        if record:
            await db.delete(record)
            count += 1
    await db.commit()
    return count


async def get_quick_templates(
    db: AsyncSession, limit: int = 10
) -> list[dict[str, Any]]:
    """Get recent records as quick-accounting templates."""
    query = (
        select(Record)
        .order_by(Record.updated_at.desc())
        .limit(limit)
    )
    result = await db.exec(query)
    records = list(result.all())
    items = []
    for record in records:
        items.append(await _enrich_record(db, record))
    return items


async def _enrich_record(
    db: AsyncSession, record: Record
) -> dict[str, Any]:
    """Enrich a record with category name/icon, tag, and attachment IDs."""
    category_name = ""
    category_icon = ""
    category = await db.get(Category, record.category_id)
    if category:
        category_name = category.name
        category_icon = category.icon

    # Get single tag (v1.1: one-to-one)
    tag_info = None
    if record.tag_id:
        tag = await db.get(Tag, record.tag_id)
        if tag:
            tag_info = {
                "id": tag.id,
                "name": tag.name,
                "category_id": tag.category_id,
            }

    # Get attachments
    att_stmt = select(Attachment.id).where(Attachment.record_id == record.id)
    att_result = await db.exec(att_stmt)
    attachment_ids = list(att_result.all())

    return {
        "id": record.id,
        "amount": record.amount,
        "type": record.type,
        "category_id": record.category_id,
        "category_name": category_name,
        "category_icon": category_icon,
        "tag": tag_info,
        "attachment_ids": attachment_ids,
        "consume_time": record.consume_time,
        "note": record.note,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
