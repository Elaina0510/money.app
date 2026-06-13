"""History service for operation history management and rollback."""

import json
from datetime import datetime
from typing import Any

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.operation_history import OperationHistory
from app.models.record import Record


async def get_history_list(
    db: AsyncSession, user_id: int | None, page: int = 1, page_size: int = 20
) -> dict[str, Any]:
    """Get paginated history list."""
    query = select(OperationHistory).where(OperationHistory.user_id == user_id)
    count_query = select(func.count(OperationHistory.id)).where(OperationHistory.user_id == user_id)

    # Get total count
    count_result = await db.exec(count_query)
    total = count_result.one()

    # Apply sorting and pagination
    query = query.order_by(OperationHistory.created_at.desc())
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.exec(query)
    entries = list(result.all())

    items = []
    for entry in entries:
        # Calculate affected_count
        affected_count = 0
        if entry.operation_type in ("create", "csv_import", "sql_import"):
            if entry.snapshot_after:
                try:
                    affected_count = len(json.loads(entry.snapshot_after))
                except (json.JSONDecodeError, TypeError):
                    affected_count = 0
        elif entry.operation_type in ("delete", "batch_delete"):
            if entry.snapshot_before:
                try:
                    affected_count = len(json.loads(entry.snapshot_before))
                except (json.JSONDecodeError, TypeError):
                    affected_count = 0
        elif entry.operation_type == "update":
            affected_count = 1

        items.append({
            "id": entry.id,
            "operation_type": entry.operation_type,
            "description": entry.description,
            "affected_count": affected_count,
            "created_at": entry.created_at,
        })

    return {"total": total, "items": items}


async def get_history_detail(
    db: AsyncSession, user_id: int | None, history_id: int
) -> dict[str, Any] | None:
    """Get history detail with parsed snapshots."""
    entry = await db.get(OperationHistory, history_id)
    if not entry or entry.user_id != user_id:
        return None

    snapshot_before = None
    snapshot_after = None
    if entry.snapshot_before:
        try:
            snapshot_before = json.loads(entry.snapshot_before)
        except (json.JSONDecodeError, TypeError):
            snapshot_before = None
    if entry.snapshot_after:
        try:
            snapshot_after = json.loads(entry.snapshot_after)
        except (json.JSONDecodeError, TypeError):
            snapshot_after = None

    return {
        "id": entry.id,
        "operation_type": entry.operation_type,
        "description": entry.description,
        "snapshot_before": snapshot_before,
        "snapshot_after": snapshot_after,
        "created_at": entry.created_at,
    }


async def rollback_operation(
    db: AsyncSession, user_id: int | None, history_id: int
) -> dict[str, Any]:
    """Execute rollback for a history entry."""
    entry = await db.get(OperationHistory, history_id)
    if not entry:
        raise ValueError("历史记录不存在")
    if entry.user_id != user_id:
        raise PermissionError("无权操作")

    operation_type = entry.operation_type
    snapshot_before = json.loads(entry.snapshot_before) if entry.snapshot_before else []
    snapshot_after = json.loads(entry.snapshot_after) if entry.snapshot_after else []

    restored_count = 0
    deleted_count = 0
    skipped_count = 0

    if operation_type in ("create", "csv_import", "sql_import"):
        # Delete records that were created
        for record_data in snapshot_after:
            record_id = record_data.get("id")
            if record_id:
                record = await db.get(Record, record_id)
                if record and record.user_id == user_id:
                    await db.delete(record)
                    deleted_count += 1
    elif operation_type in ("delete", "batch_delete"):
        # Restore deleted records
        for record_data in snapshot_before:
            record_id = record_data.get("id")
            if record_id:
                # Check if ID is already taken
                existing = await db.get(Record, record_id)
                if existing:
                    skipped_count += 1
                    continue
                # Restore the record with original values
                record = Record(
                    id=record_id,
                    user_id=record_data.get("user_id"),
                    amount=record_data.get("amount"),
                    type=record_data.get("type"),
                    category_id=record_data.get("category_id"),
                    tag_id=record_data.get("tag_id"),
                    consume_time=record_data.get("consume_time"),
                    note=record_data.get("note"),
                    created_at=record_data.get("created_at"),
                    updated_at=record_data.get("updated_at"),
                )
                db.add(record)
                restored_count += 1
    elif operation_type == "update":
        # Restore the previous state
        for record_data in snapshot_before:
            record_id = record_data.get("id")
            if record_id:
                record = await db.get(Record, record_id)
                if record and record.user_id == user_id:
                    record.amount = record_data.get("amount", record.amount)
                    record.type = record_data.get("type", record.type)
                    record.category_id = record_data.get("category_id", record.category_id)
                    record.tag_id = record_data.get("tag_id")
                    record.consume_time = record_data.get("consume_time", record.consume_time)
                    record.note = record_data.get("note")
                    record.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    restored_count += 1

    # Delete the history entry itself
    await db.delete(entry)
    await db.commit()

    return {
        "operation_type": operation_type,
        "restored_count": restored_count,
        "deleted_count": deleted_count,
        "skipped_count": skipped_count,
    }
