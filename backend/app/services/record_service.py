"""Record business logic."""

from datetime import datetime
from typing import Any

from sqlmodel import select, func, or_
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.record import Record
from app.models.record_tag import RecordTag
from app.models.tag import Tag
from app.models.category import Category
from app.models.attachment import Attachment
from app.schemas.record import RecordCreate, RecordUpdate
from app.utils.response import Code


async def create_record(
    db: AsyncSession, data: RecordCreate
) -> Record:
    """Create a new record with tags."""
    # Validate category exists
    category = await db.get(Category, data.category_id)
    if not category:
        raise ValueError("分类不存在")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record = Record(
        amount=data.amount,
        type=data.type,
        category_id=data.category_id,
        date=data.date,
        created_at=data.created_at or now,
        updated_at=now,
    )
    db.add(record)
    await db.flush()

    # Process tags
    if data.tags:
        for tag_name in data.tags:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            # Find or create tag
            stmt = select(Tag).where(Tag.name == tag_name)
            result = await db.exec(stmt)
            tag = result.first()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
                await db.flush()
            rt = RecordTag(record_id=record.id, tag_id=tag.id)
            db.add(rt)

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
    tag: str | None = None,
    keyword: str | None = None,
    sort_by: str = "date",
    sort_order: str = "desc",
) -> dict[str, Any]:
    """Get paginated records with optional filters."""
    query = select(Record)
    count_query = select(func.count(Record.id))

    # Apply filters
    if start_date:
        query = query.where(Record.date >= start_date)
        count_query = count_query.where(Record.date >= start_date)
    if end_date:
        query = query.where(Record.date <= end_date)
        count_query = count_query.where(Record.date <= end_date)
    if category_id:
        query = query.where(Record.category_id == category_id)
        count_query = count_query.where(Record.category_id == category_id)
    if type_filter:
        query = query.where(Record.type == type_filter)
        count_query = count_query.where(Record.type == type_filter)
    if keyword:
        # Search in tags via record_tags + tags table
        # For keyword search, we need to look at tag names
        tag_subquery = select(RecordTag.record_id).join(Tag).where(
            Tag.name.contains(keyword)
        )
        query = query.where(
            or_(Record.id.in_(tag_subquery))
        )
        count_query = count_query.where(
            or_(Record.id.in_(tag_subquery))
        )

    # Get total count
    count_result = await db.exec(count_query)
    total = count_result.one()

    # Apply sorting
    sort_column = getattr(Record, sort_by, Record.date)
    if sort_order == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.exec(query)
    records = list(result.all())

    # Enrich records with category names, tags, and attachments
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
    tags = update_data.pop("tags", None)

    for key, value in update_data.items():
        setattr(record, key, value)

    record.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update tags if provided
    if tags is not None:
        # Remove existing tag associations
        old_rt_stmt = select(RecordTag).where(RecordTag.record_id == record_id)
        old_rt_result = await db.exec(old_rt_stmt)
        for rt in old_rt_result:
            await db.delete(rt)

        # Add new tags
        for tag_name in tags:
            tag_name = tag_name.strip()
            if not tag_name:
                continue
            stmt = select(Tag).where(Tag.name == tag_name)
            result = await db.exec(stmt)
            tag = result.first()
            if not tag:
                tag = Tag(name=tag_name)
                db.add(tag)
                await db.flush()
            rt = RecordTag(record_id=record.id, tag_id=tag.id)
            db.add(rt)

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
        .order_by(Record.created_at.desc())
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
    """Enrich a record with category name, tags, and attachment IDs."""
    # Get category name
    category_name = ""
    category = await db.get(Category, record.category_id)
    if category:
        category_name = category.name

    # Get tags
    tag_stmt = (
        select(Tag.name)
        .join(RecordTag, Tag.id == RecordTag.tag_id)
        .where(RecordTag.record_id == record.id)
    )
    tag_result = await db.exec(tag_stmt)
    tags = list(tag_result.all())

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
        "tags": tags,
        "attachment_ids": attachment_ids,
        "date": record.date,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }
