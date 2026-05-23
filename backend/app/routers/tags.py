"""Tag API router."""

from fastapi import APIRouter, Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.tag import TagCreate, TagResponse, TagUpdate
from app.services import tag_service
from app.utils.auth import get_current_user
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/tags", tags=["标签管理"])


@router.get("")
async def list_tags(
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Get all tags."""
    tags = await tag_service.get_tags(db, current_user)
    return success_response(
        data=[TagResponse.model_validate(t, from_attributes=True).model_dump() for t in tags]
    )


@router.get("/{tag_id}")
async def get_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Get a single tag with its associated category."""
    tag = await tag_service.get_tag(db, tag_id)
    if not tag:
        return error_response(Code.NOT_FOUND, "标签不存在")
    return success_response(data=tag)


@router.post("")
async def create_tag(
    data: TagCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Create a new tag."""
    try:
        tag = await tag_service.create_tag(db, data, current_user)
        return success_response(
            data=TagResponse.model_validate(tag, from_attributes=True).model_dump(),
            message="标签创建成功",
        )
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))


@router.put("/{tag_id}")
async def update_tag(
    tag_id: int,
    data: TagUpdate,
    db: AsyncSession = Depends(get_session),
):
    """Update a tag."""
    try:
        tag = await tag_service.update_tag(db, tag_id, data)
        if not tag:
            return error_response(Code.NOT_FOUND, "标签不存在")
        return success_response(
            data=TagResponse.model_validate(tag, from_attributes=True).model_dump(),
            message="标签更新成功",
        )
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete a tag."""
    result = await tag_service.delete_tag(db, tag_id)
    if result:
        return error_response(result["code"], result["message"])
    return success_response(message="标签删除成功")
