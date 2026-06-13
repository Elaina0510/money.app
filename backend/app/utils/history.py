"""History recording utility functions."""

import json
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.operation_history import OperationHistory
from app.models.record import Record


def record_to_dict(record: Record) -> dict[str, Any]:
    """Convert a Record ORM object to a serializable dict for snapshots."""
    return {
        "id": record.id,
        "user_id": record.user_id,
        "amount": record.amount,
        "type": record.type,
        "category_id": record.category_id,
        "tag_id": record.tag_id,
        "consume_time": record.consume_time,
        "note": record.note,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


async def create_history_entry(
    db: AsyncSession,
    user_id: int | None,
    operation_type: str,
    description: str,
    snapshot_before: list[dict[str, Any]] | None = None,
    snapshot_after: list[dict[str, Any]] | None = None,
) -> OperationHistory:
    """Create a history entry and auto-cleanup old entries."""
    entry = OperationHistory(
        user_id=user_id,
        operation_type=operation_type,
        description=description,
        snapshot_before=(
            json.dumps(snapshot_before, ensure_ascii=False) if snapshot_before else None
        ),
        snapshot_after=(
            json.dumps(snapshot_after, ensure_ascii=False) if snapshot_after else None
        ),
    )
    db.add(entry)
    await db.flush()

    # Auto-cleanup old entries
    await cleanup_old_history(db, user_id)

    return entry


async def cleanup_old_history(
    db: AsyncSession, user_id: int | None, max_count: int = 30
) -> None:
    """Keep only the latest max_count history entries for a user."""
    # Query entries for this user, ordered by created_at DESC
    query = (
        select(OperationHistory)
        .where(OperationHistory.user_id == user_id)
        .order_by(OperationHistory.created_at.desc())
        .offset(max_count)
    )
    result = await db.exec(query)
    old_entries = list(result.all())

    for entry in old_entries:
        await db.delete(entry)
