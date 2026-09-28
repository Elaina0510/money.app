"""Tag API router."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.tag import TagBatchDelete, TagCreate, TagResponse, TagUpdate
from app.services import tag_service
from app.utils.auth import require_auth
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/tags", tags=["标签管理"])


@router.get("")
async def list_tags(
    q: str | None = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get all tags, optionally filtered by search keyword."""
    tags = await tag_service.get_tags(db, current_user, search=q)
    return success_response(
        data=[TagResponse.model_validate(t, from_attributes=True).model_dump() for t in tags]
    )


@router.get("/paged")
async def list_tags_paged(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    q: str | None = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get tags with pagination: {items, total, page, page_size}.

    v1.4.2 M5 新增，供标签管理二级页「展开更多」使用；total 为匹配总数（含 q）。
    路由顺序红线：必须声明在 GET /{tag_id} 之前，否则 "paged" 被 int 路径参数
    抢匹配 → 422。
    """
    tags, total = await tag_service.get_tags_paged(
        db, current_user, search=q, page=page, page_size=page_size
    )
    return success_response(
        data={
            "items": [
                TagResponse.model_validate(t, from_attributes=True).model_dump() for t in tags
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/batch-delete")
async def batch_delete_tags(
    data: TagBatchDelete,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Soft-delete a batch of the current user's tags atomically (v1.4.4 M1 / REQ-002).

    命中数与 `len(set(ids))` 不符 → service 抛中文 ValueError → 400 `PARAM_ERROR`，
    整单零落删除（原子性）。跨用户 id 与 `user_id IS NULL` 全局行同样计入「不存在」
    （红线 10：本接口刻意不开全局行口子）。
    ids 缺失/空数组/非整数由 FastAPI 默认 422 兜底（不做特判——前端仅在已选 ≥1 时发起）。
    """
    try:
        count = await tag_service.batch_delete_tags(db, data.ids, current_user)
        return success_response(
            data={"deleted_count": count}, message=f"已删除 {count} 个标签"
        )
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))


@router.post("/clear-all")
async def clear_all_tags(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Soft-delete every tag of the current user (v1.4.4 M1 / REQ-001, no request body).

    0 条也是成功（幂等）：`deleted_count=0` 时 message 为「标签已全部清空」。
    全局预设行（`user_id IS NULL`）不在触碰范围内（红线 10）；未登录沿用全局 401。
    """
    count = await tag_service.clear_all_tags(db, current_user)
    message = f"已清空 {count} 个标签" if count else "标签已全部清空"
    return success_response(data={"deleted_count": count}, message=message)


@router.get("/{tag_id}")
async def get_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get a single tag with its associated category."""
    tag = await tag_service.get_tag(db, tag_id, current_user)
    if not tag:
        return error_response(Code.NOT_FOUND, "标签不存在")
    return success_response(data=tag)


@router.post("")
async def create_tag(
    data: TagCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
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
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Update a tag."""
    try:
        result = await tag_service.update_tag(db, tag_id, data, current_user)
        if result is None:
            return error_response(Code.NOT_FOUND, "标签不存在")
        if isinstance(result, dict):
            return error_response(result["code"], result["message"], status_code=403)
        return success_response(
            data=TagResponse.model_validate(result, from_attributes=True).model_dump(),
            message="标签更新成功",
        )
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Delete a tag."""
    result = await tag_service.delete_tag(db, tag_id, current_user)
    if result:
        status = 403 if result["code"] == Code.FORBIDDEN else 400
        return error_response(result["code"], result["message"], status_code=status)
    return success_response(message="标签删除成功")
