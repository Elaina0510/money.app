"""Tag business logic."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.tag import Tag
from app.models.category import Category
from app.schemas.tag import TagCreate, TagUpdate
from app.utils.response import Code


async def get_tags(db: AsyncSession) -> list[Tag]:
    """Get all tags."""
    query = select(Tag).order_by(Tag.id)
    result = await db.exec(query)
    return list(result.all())


async def get_tag(db: AsyncSession, tag_id: int) -> dict | None:
    """Get a single tag with its associated category."""
    tag = await db.get(Tag, tag_id)
    if not tag:
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


async def create_tag(db: AsyncSession, data: TagCreate) -> Tag:
    """Create a new tag, optionally with category_id."""
    # Validate category exists if provided
    if data.category_id:
        category = await db.get(Category, data.category_id)
        if not category:
            raise ValueError("关联的分类不存在")
    tag = Tag(name=data.name, category_id=data.category_id)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(
    db: AsyncSession, tag_id: int, data: TagUpdate
) -> Tag | None:
    """Update a tag name and/or category_id."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return None
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


async def delete_tag(db: AsyncSession, tag_id: int) -> dict | None:
    """Delete a tag. Returns None if successful, or an error dict."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return {"code": Code.NOT_FOUND, "message": "标签不存在"}
    await db.delete(tag)
    await db.commit()
    return None
