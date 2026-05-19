"""Tag business logic."""

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.tag import Tag
from app.models.record_tag import RecordTag
from app.schemas.tag import TagCreate, TagUpdate
from app.utils.response import Code


async def get_tags(db: AsyncSession) -> list[Tag]:
    """Get all tags."""
    query = select(Tag).order_by(Tag.id)
    result = await db.exec(query)
    return list(result.all())


async def create_tag(db: AsyncSession, data: TagCreate) -> Tag:
    """Create a new tag."""
    tag = Tag(name=data.name)
    db.add(tag)
    await db.commit()
    await db.refresh(tag)
    return tag


async def update_tag(
    db: AsyncSession, tag_id: int, data: TagUpdate
) -> Tag | None:
    """Update a tag name."""
    tag = await db.get(Tag, tag_id)
    if not tag:
        return None
    tag.name = data.name
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
