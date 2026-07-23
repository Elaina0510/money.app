"""Category API router."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services import category_service
from app.utils.auth import require_auth
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/categories", tags=["分类管理"])


@router.get("")
async def list_categories(
    type: str | None = Query(None, description="筛选类型: income/expense"),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get all categories, optionally filtered by type."""
    categories = await category_service.get_categories(db, type, current_user)
    items = [
        CategoryResponse.model_validate(c, from_attributes=True).model_dump() for c in categories
    ]
    return success_response(data=items)


@router.post("")
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Create a new custom category."""
    try:
        category = await category_service.create_category(db, data, current_user)
        return success_response(
            data=CategoryResponse.model_validate(category, from_attributes=True).model_dump(),
            message="分类创建成功",
        )
    except ValueError as e:
        return error_response(Code.CONFLICT, str(e))
    except Exception as e:
        if "UNIQUE constraint" in str(e):
            return error_response(Code.CONFLICT, "该名称的分类已存在")
        raise


@router.put("/{category_id}")
async def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Update an existing category."""
    try:
        category = await category_service.update_category(db, category_id, data, current_user)
        if not category:
            return error_response(Code.NOT_FOUND, "分类不存在")
        return success_response(
            data=CategoryResponse.model_validate(category, from_attributes=True).model_dump(),
            message="分类更新成功",
        )
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e), status_code=403)


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Delete a category and cascade-delete its records and budgets."""
    try:
        result = await category_service.delete_category(db, category_id, current_user)
        if result is None:
            return error_response(Code.NOT_FOUND, "分类不存在")
        record_count = result["deleted_records"]
        if record_count > 0:
            return success_response(
                data=result,
                message=f"分类删除成功，同时删除了 {record_count} 条关联账单",
            )
        return success_response(data=result, message="分类删除成功")
    except PermissionError as e:
        return error_response(Code.FORBIDDEN, str(e), status_code=403)


@router.post("/restore-defaults")
async def restore_defaults(
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Restore default category settings."""
    result = await category_service.restore_default_categories(db, current_user)
    return success_response(
        data=result,
        message=f"已恢复默认分类，删除 {result['deleted_categories']} 个自定义分类，"
                f"{result['affected_records']} 条记录已解除分类关联",
    )
