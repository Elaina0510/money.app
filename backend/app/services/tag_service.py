"""Tag business logic."""

from datetime import datetime
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.category import Category
from app.models.tag import Tag
from app.models.user import User
from app.schemas.tag import TagCreate, TagUpdate
from app.utils.response import Code


async def get_tags(
    db: AsyncSession, current_user: User | None = None, search: str | None = None
) -> list[Tag]:
    """Get all tags visible to the user, excluding soft-deleted tags."""
    query = select(Tag).where(Tag.deleted_at.is_(None)).order_by(Tag.id)
    if current_user:
        query = query.where(Tag.user_id == current_user.id)
    else:
        query = query.where(Tag.user_id.is_(None))
    if search:
        query = query.where(Tag.name.contains(search))
    query = query.limit(20)
    result = await db.exec(query)
    return list(result.all())


async def get_tag(
    db: AsyncSession, tag_id: int, current_user: User | None = None
) -> dict[str, Any] | None:
    """Get a single tag with its associated category.

    IDOR 防护:非归属者视为不存在(返回 None → 404)。
    """
    tag = await db.get(Tag, tag_id)
    if not tag:
        return None
    if current_user is not None and tag.user_id != current_user.id:
        return None
    category_name = None
    if tag.category_id:
        category = await db.get(Category, tag.category_id)
        if category:
            category_name = category.name
    return {
        "id": tag.id,
        "name": tag.name,
        "category_id": tag.category_id,
        "category_name": category_name,
        "created_at": tag.created_at,
    }


async def create_tag(db: AsyncSession, data: TagCreate, current_user: User | None = None) -> Tag:
    """Create a new tag, optionally with category_id."""
    # Validate category exists if provided
    if data.category_id:
        category = await db.get(Category, data.category_id)
        if not category:
            raise ValueError("关联的分类不存在")
    tag = Tag(
        name=data.name,
        category_id=data.category_id,
        user_id=current_user.id if current_user else None,
    )
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(
    db: AsyncSession,
    tag_id: int,
    data: TagUpdate,
    current_user: User | None = None,
) -> Tag | dict[str, Any] | None:
    """Update a tag name and/or category_id."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return None

    # Ownership check
    if tag.user_id is not None and (current_user is None or tag.user_id != current_user.id):
        return {"code": Code.FORBIDDEN, "message": "无权操作"}

    update_data = data.model_dump(exclude_unset=True)
    # Validate category exists if being set
    if "category_id" in update_data and update_data["category_id"] is not None:
        category = await db.get(Category, update_data["category_id"])
        if not category:
            raise ValueError("关联的分类不存在")
    for key, value in update_data.items():
        setattr(tag, key, value)
    await db.commit()
    await db.refresh(tag)
    return tag


async def delete_tag(
    db: AsyncSession, tag_id: int, current_user: User | None = None
) -> dict[str, Any] | None:
    """Soft-delete a tag by setting deleted_at. Returns None if successful, or an error dict."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return {"code": Code.NOT_FOUND, "message": "标签不存在"}

    # Ownership check
    if tag.user_id is not None and (current_user is None or tag.user_id != current_user.id):
        return {"code": Code.FORBIDDEN, "message": "无权操作"}

    tag.deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await db.commit()
    return None
