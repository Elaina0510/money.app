"""Record business logic."""

from datetime import datetime
from typing import Any

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.attachment import Attachment
from app.models.category import Category
from app.models.quick_template import QuickTemplate
from app.models.record import Record
from app.models.tag import Tag
from app.models.user import User
from app.schemas.record import RecordCreate, RecordUpdate
from app.utils.history import create_history_entry, record_to_dict
from app.utils.money import round_money


async def create_record(
    db: AsyncSession, data: RecordCreate, current_user: User | None = None
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
        amount=round_money(data.amount),
        type=data.type,
        category_id=data.category_id,
        tag_id=data.tag_id,
        consume_time=consume_time,
        note=data.note,
        user_id=current_user.id if current_user else None,
        created_at=now,
        updated_at=now,
    )
    db.add(record)
    await db.flush()

    # Write history entry
    user_id = current_user.id if current_user else None
    amount_str = f"¥{record.amount:.2f}"
    tag_name = ""
    if record.tag_id:
        tag_obj = await db.get(Tag, record.tag_id)
        if tag_obj:
            tag_name = f" - {tag_obj.name}"
    await create_history_entry(
        db, user_id, "create",
        f"新增账单 {amount_str}{tag_name}",
        snapshot_after=[record_to_dict(record)],
    )

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
    current_user: User | None = None,
) -> dict[str, Any]:
    """Get paginated records with optional filters."""
    query = select(Record)
    count_query = select(func.count(Record.id))

    # Data isolation: filter by user_id
    if current_user:
        query = query.where(Record.user_id == current_user.id)
        count_query = count_query.where(Record.user_id == current_user.id)
    else:
        query = query.where(Record.user_id.is_(None))
        count_query = count_query.where(Record.user_id.is_(None))

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
    _valid_sort_by = {"consume_time", "amount", "created_at", "updated_at"}
    if sort_by not in _valid_sort_by:
        sort_by = "consume_time"
    _valid_sort_order = {"asc", "desc"}
    if sort_order not in _valid_sort_order:
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


async def get_record(
    db: AsyncSession, record_id: int, current_user: User | None = None
) -> dict[str, Any] | None:
    """Get a single record with full details.

    IDOR 防护:非归属者视为不存在(返回 None → 404,避免泄露存在性)。
    """
    record = await db.get(Record, record_id)
    if not record:
        return None
    if current_user is not None and record.user_id != current_user.id:
        return None
    return await _enrich_record(db, record)


async def enrich_record(db: AsyncSession, record: Record) -> dict[str, Any]:
    """Public wrapper for _enrich_record (供 router 调用)。"""
    return await _enrich_record(db, record)


async def update_record(
    db: AsyncSession,
    record_id: int,
    data: RecordUpdate,
    current_user: User | None = None,
) -> dict[str, Any] | None:
    """Update an existing record."""
    record = await db.get(Record, record_id)
    if not record:
        return None

    # Ownership check
    if record.user_id is not None and (current_user is None or record.user_id != current_user.id):
        raise PermissionError("无权操作")

    # Save snapshot before update
    old_dict = record_to_dict(record)

    update_data = data.model_dump(exclude_unset=True)

    # Validate tag exists if tag_id is provided
    if "tag_id" in update_data and update_data["tag_id"] is not None:
        tag = await db.get(Tag, update_data["tag_id"])
        if not tag:
            raise ValueError("标签不存在")

    for key, value in update_data.items():
        setattr(record, key, value)
    # 金额边界:统一两位小数,避免 float 尾差
    if "amount" in update_data and record.amount is not None:
        record.amount = round_money(record.amount)

    record.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.flush()

    # Write history entry
    new_dict = record_to_dict(record)
    user_id = current_user.id if current_user else None
    old_amount = f"¥{old_dict['amount']:.2f}"
    new_amount = f"¥{new_dict['amount']:.2f}"
    tag_name = ""
    if record.tag_id:
        tag_obj = await db.get(Tag, record.tag_id)
        if tag_obj:
            tag_name = f" - {tag_obj.name}"
    await create_history_entry(
        db, user_id, "update",
        f"修改账单 {old_amount} → {new_amount}{tag_name}",
        snapshot_before=[old_dict],
        snapshot_after=[new_dict],
    )

    await db.commit()
    await db.refresh(record)
    return await _enrich_record(db, record)


async def delete_record(db: AsyncSession, record_id: int, current_user: User | None = None) -> bool:
    """Delete a record. Returns True if deleted, False if not found."""
    record = await db.get(Record, record_id)
    if not record:
        return False

    # Ownership check
    if record.user_id is not None and (current_user is None or record.user_id != current_user.id):
        raise PermissionError("无权操作")

    # Save snapshot before delete
    deleted_dict = record_to_dict(record)
    user_id = current_user.id if current_user else None
    amount_str = f"¥{record.amount:.2f}"
    tag_name = ""
    if record.tag_id:
        tag_obj = await db.get(Tag, record.tag_id)
        if tag_obj:
            tag_name = f" - {tag_obj.name}"
    await create_history_entry(
        db, user_id, "delete",
        f"删除账单 {amount_str}{tag_name}",
        snapshot_before=[deleted_dict],
    )

    await db.delete(record)
    await db.commit()
    return True


async def batch_delete_records(
    db: AsyncSession, ids: list[int], current_user: User | None = None
) -> int:
    """Delete multiple records. Returns the number deleted."""
    deleted_records = []
    for rid in ids:
        record = await db.get(Record, rid)
        if record:
            # Ownership check
            if record.user_id is not None and (
                current_user is None or record.user_id != current_user.id
            ):
                raise PermissionError("无权操作")
            deleted_records.append(record)

    # Write history entry before deleting
    if deleted_records:
        user_id = current_user.id if current_user else None
        snapshots = [record_to_dict(r) for r in deleted_records]
        await create_history_entry(
            db, user_id, "batch_delete",
            f"批量删除 {len(deleted_records)} 条账单",
            snapshot_before=snapshots,
        )

    for record in deleted_records:
        await db.delete(record)
    await db.commit()
    return len(deleted_records)


async def get_quick_templates(
    db: AsyncSession, limit: int = 10, current_user: User | None = None
) -> list[dict[str, Any]]:
    """Get quick-accounting templates: auto (from records with count >= 2) + manual."""
    if current_user:
        user_filter = Record.user_id == current_user.id
        qt_user_filter = QuickTemplate.user_id == current_user.id
    else:
        user_filter = Record.user_id.is_(None)
        qt_user_filter = QuickTemplate.user_id.is_(None)

    # Auto templates: group by (tag_id, type, amount), filter count >= 2
    auto_query = (
        select(
            Record.tag_id,
            Record.type,
            Record.amount,
            func.count(Record.id).label("count"),
            func.max(Record.updated_at).label("last_used"),
        )
        .where(user_filter)
        .where(Record.tag_id.isnot(None))
        .group_by(Record.tag_id, Record.type, Record.amount)
        .having(func.count(Record.id) >= 2)
        .order_by(func.max(Record.updated_at).desc())
        .limit(limit)
    )
    auto_result = await db.exec(auto_query)
    auto_rows = auto_result.all()

    templates = []
    seen_keys = set()
    for row in auto_rows:
        tag = await db.get(Tag, row.tag_id)
        if not tag or tag.deleted_at:
            continue
        category = await db.get(Category, tag.category_id) if tag.category_id else None
        key = (row.tag_id, row.type, row.amount)
        seen_keys.add(key)
        templates.append({
            "tag_id": row.tag_id,
            "tag_name": tag.name,
            "type": row.type,
            "amount": round_money(row.amount),
            "category_id": tag.category_id,
            "category_name": category.name if category else "",
            "category_icon": category.icon if category else "mdi-circle",
            "count": row.count,
            "source": "auto",
        })

    # Manual templates
    manual_query = (
        select(QuickTemplate)
        .where(qt_user_filter)
        .order_by(QuickTemplate.created_at.desc())
        .limit(limit)
    )
    manual_result = await db.exec(manual_query)
    manual_rows = manual_result.all()

    for qt in manual_rows:
        key = (qt.tag_id, qt.type, qt.amount)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        tag = await db.get(Tag, qt.tag_id) if qt.tag_id else None
        if tag and tag.deleted_at:
            continue
        category = await db.get(Category, qt.category_id) if qt.category_id else None
        templates.append({
            "id": qt.id,
            "tag_id": qt.tag_id,
            "tag_name": tag.name if tag else "",
            "type": qt.type,
            "amount": round_money(qt.amount),
            "category_id": qt.category_id,
            "category_name": category.name if category else "",
            "category_icon": category.icon if category else "mdi-circle",
            "count": 0,
            "source": "manual",
        })

    return templates[:limit]


async def add_quick_template(
    db: AsyncSession, tag_id: int, amount: float, current_user: User | None = None
) -> QuickTemplate | None:
    """Manually add a quick template."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return None
    # Derive type from tag's category
    template_type = "expense"
    if tag.category_id:
        category = await db.get(Category, tag.category_id)
        if category:
            template_type = category.type
    qt = QuickTemplate(
        user_id=current_user.id if current_user else None,
        tag_id=tag_id,
        category_id=tag.category_id,
        type=template_type,
        amount=round_money(amount),
    )
    db.add(qt)
    await db.commit()
    await db.refresh(qt)
    return qt


async def delete_quick_template(
    db: AsyncSession, template_id: int, current_user: User | None = None
) -> bool:
    """Delete a manual quick template."""
    qt = await db.get(QuickTemplate, template_id)
    if not qt:
        return False
    if qt.user_id is not None and (current_user is None or qt.user_id != current_user.id):
        return False
    await db.delete(qt)
    await db.commit()
    return True


async def _enrich_record(db: AsyncSession, record: Record) -> dict[str, Any]:
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
        "amount": round_money(record.amount),
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
