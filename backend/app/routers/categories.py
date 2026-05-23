"""Category API router."""

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services import category_service
from app.utils.auth import get_current_user
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/categories", tags=["分类管理"])


@router.get("")
async def list_categories(
    type: str | None = Query(None, description="筛选类型: income/expense"),
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
    """Get all categories, optionally filtered by type."""
    categories = await category_service.get_categories(db, type, current_user)
    return success_response(
        data=[CategoryResponse.model_validate(c, from_attributes=True).model_dump() for c in categories]
    )


@router.post("")
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_session),
    current_user: User | None = Depends(get_current_user),
):
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
):
    """Update an existing category."""
    category = await category_service.update_category(db, category_id, data)
    if not category:
        return error_response(Code.NOT_FOUND, "分类不存在")
    return success_response(
        data=CategoryResponse.model_validate(category, from_attributes=True).model_dump(),
        message="分类更新成功",
    )


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_session),
):
    """Delete a category."""
    result = await category_service.delete_category(db, category_id)
    if result:
        return error_response(result["code"], result["message"])
    return success_response(message="分类删除成功")
