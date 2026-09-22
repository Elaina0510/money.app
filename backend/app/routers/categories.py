"""Category API router."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryReorder, CategoryResponse, CategoryUpdate
from app.services import category_service
from app.utils.auth import require_auth
from app.utils.response import Code, error_response, success_response

router = APIRouter(prefix="/api/categories", tags=["分类管理"])


@router.get("")
async def list_categories(
    type: str | None = Query(
        None, description="已废弃（v1.4.3 M8）：参数保留签名但一律忽略，响应恒为全量单列表"
    ),
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Get all categories (single unified list).

    v1.4.3 M8：分类收支共用，``type`` 查询参数保留签名以兼容旧客户端，
    但服务层一律忽略（不报错、不过滤）。
    """
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
    """Create a new custom category.

    v1.4.3 M8：不再收 ``type``（分类收支共用），服务层写占位值并按 name + user_id 查重。
    """
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


@router.put("/reorder")
async def reorder_categories(
    data: CategoryReorder,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """批量重排全量分类排序（原子保存，「其他」强制置尾）。

    v1.4.3 M8：分类不再分收支两组，载荷为 ``{ids}``（全量有序 id）。
    注意：必须声明在 ``PUT /{category_id}`` 之前，否则会被路径参数抢先匹配 422。
    """
    try:
        categories = await category_service.reorder_categories(db, data.ids, current_user)
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))
    items = [
        CategoryResponse.model_validate(c, from_attributes=True).model_dump() for c in categories
    ]
    return success_response(data=items, message="排序已保存")


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
    except ValueError as e:
        return error_response(Code.PARAM_ERROR, str(e))


@router.delete("/{category_id}")
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_auth),
) -> JSONResponse:
    """Delete a category and cascade-delete its records; budgets go dormant."""
    try:
        result = await category_service.delete_category(db, category_id, current_user)
        if result is None:
            return error_response(Code.NOT_FOUND, "分类不存在")
        record_count = result["deleted_records"]
        # v1.4.3-boot2 M3（任务 3.4 / 决策 D4）：include 预算失去最后一个关联分类
        # 不再被删除，改置 dormant=1 休眠保留 → 提示语从「删除了 N 条预算」改向为
        # 「保留为休眠」，且 M=0 时整句不提（计数键同改 dormant_budgets）
        dormant_count = result.get("dormant_budgets", 0)
        message = "分类删除成功"
        if record_count > 0:
            message += f"，同时删除了 {record_count} 条关联账单"
        if dormant_count > 0:
            message += f"，{dormant_count} 条预算因不再覆盖任何分类被保留为休眠"
        return success_response(data=result, message=message)
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
